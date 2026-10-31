using System.Diagnostics;
using System.Text;
using System.Text.Json;
using Atlas.Application.AI;
using Atlas.Contracts.AI;

namespace Atlas.AI;

/// <summary>
/// Optional local Hermes Agent adapter. It mirrors the previous Atlas bridge:
/// Hermes runs in a killable child process with web-only tool access.
/// </summary>
public sealed class HermesAgentProvider : IModelProvider
{
    private const int MaxTaskLength = 3_000;
    private const int MaxOutputLength = 20_000;

    private const string WorkerScript = """
        import contextlib
        import json
        import sys

        payload = json.load(sys.stdin)
        sys.path.insert(0, payload["hermes_path"])

        try:
            from run_agent import AIAgent

            agent = AIAgent(
                model=payload["model"],
                quiet_mode=True,
                skip_context_files=True,
                skip_memory=True,
                enabled_toolsets=["web"],
                disabled_toolsets=[
                    "terminal", "file", "computer", "code_execution", "browser"
                ],
            )
            task_prompt = (
                "Execute esta tarefa usando somente ferramentas de pesquisa web disponíveis. "
                "Não afirme ter alterado arquivos, sistemas ou contas. Se a tarefa exigir "
                "ações fora da pesquisa web, explique essa limitação.\n\n"
                "Tarefa solicitada pelo usuário:\n" + payload["task"]
            )
            with contextlib.redirect_stdout(sys.stderr):
                result = agent.chat(task_prompt)
            if not isinstance(result, str) or not result.strip():
                raise RuntimeError("Hermes Agent retornou uma resposta vazia.")
            json.dump({"result": result.strip()[:20000]}, sys.stdout, ensure_ascii=False)
        except Exception as exc:
            json.dump({"error": str(exc)[:1000]}, sys.stdout, ensure_ascii=False)
            sys.exit(1)
        """;

    private static readonly string[] AllowedEnvironmentKeys =
    [
        "PATH", "HOME", "USERPROFILE", "TMP", "TEMP", "SYSTEMROOT",
        "APPDATA", "LOCALAPPDATA", "GEMINI_API_KEY", "GOOGLE_API_KEY",
        "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY",
        "TOGETHER_API_KEY", "FIREWORKS_API_KEY", "MISTRAL_API_KEY"
    ];

    public string Name => "Hermes Agent";

    public async Task<ModelResponse> GenerateAsync(ModelRequest request, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(request);
        ArgumentException.ThrowIfNullOrWhiteSpace(request.Prompt);
        if (request.Prompt.Length > MaxTaskLength)
            throw new ArgumentException($"A tarefa Hermes deve ter no máximo {MaxTaskLength} caracteres.");

        var enabled = string.Equals(
            Environment.GetEnvironmentVariable("ATLAS_HERMES_ENABLED"), "true",
            StringComparison.OrdinalIgnoreCase);
        if (!enabled)
            throw new InvalidOperationException("Hermes está desativado. Configure ATLAS_HERMES_ENABLED=true.");

        var hermesPathValue = Environment.GetEnvironmentVariable("ATLAS_HERMES_PATH");
        if (string.IsNullOrWhiteSpace(hermesPathValue))
            throw new InvalidOperationException("Configure ATLAS_HERMES_PATH para o checkout local do Hermes Agent.");

        var hermesPath = Path.GetFullPath(Environment.ExpandEnvironmentVariables(hermesPathValue));
        if (!Directory.Exists(hermesPath) || !File.Exists(Path.Combine(hermesPath, "run_agent.py")))
            throw new InvalidOperationException("ATLAS_HERMES_PATH deve conter o arquivo run_agent.py.");

        var model = Environment.GetEnvironmentVariable("ATLAS_HERMES_MODEL")?.Trim();
        if (string.IsNullOrWhiteSpace(model))
            throw new InvalidOperationException("Configure ATLAS_HERMES_MODEL.");

        var python = Environment.GetEnvironmentVariable("ATLAS_HERMES_PYTHON")?.Trim();
        if (string.IsNullOrWhiteSpace(python)) python = "python";

        var timeoutSeconds = 180;
        var timeoutValue = Environment.GetEnvironmentVariable("ATLAS_HERMES_TIMEOUT_SECONDS");
        if (!string.IsNullOrWhiteSpace(timeoutValue) &&
            (!int.TryParse(timeoutValue, out timeoutSeconds) || timeoutSeconds is < 10 or > 900))
            throw new InvalidOperationException("ATLAS_HERMES_TIMEOUT_SECONDS deve estar entre 10 e 900.");

        var task = BuildTask(request);
        var payload = JsonSerializer.Serialize(new { hermes_path = hermesPath, model, task });
        var startInfo = new ProcessStartInfo
        {
            FileName = python,
            WorkingDirectory = hermesPath,
            UseShellExecute = false,
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true
        };
        startInfo.ArgumentList.Add("-I");
        startInfo.ArgumentList.Add("-c");
        startInfo.ArgumentList.Add(WorkerScript);

        var inherited = new Dictionary<string, string?>(StringComparer.OrdinalIgnoreCase);
        foreach (var key in AllowedEnvironmentKeys)
            inherited[key] = Environment.GetEnvironmentVariable(key);
        startInfo.Environment.Clear();
        foreach (var pair in inherited)
            if (!string.IsNullOrWhiteSpace(pair.Value))
                startInfo.Environment[pair.Key] = pair.Value;

        using var process = new Process { StartInfo = startInfo };
        var processStarted = false;
        try
        {
            if (!process.Start())
                throw new InvalidOperationException("Não foi possível iniciar o processo isolado do Hermes.");
            processStarted = true;

            await process.StandardInput.WriteAsync(payload.AsMemory(), cancellationToken);
            process.StandardInput.Close();

            using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            timeout.CancelAfter(TimeSpan.FromSeconds(timeoutSeconds));
            var stdoutTask = process.StandardOutput.ReadToEndAsync(timeout.Token);
            var stderrTask = process.StandardError.ReadToEndAsync(timeout.Token);

            try
            {
                await process.WaitForExitAsync(timeout.Token);
            }
            catch (OperationCanceledException)
            {
                TryKill(process);
                if (cancellationToken.IsCancellationRequested) throw;
                throw new TimeoutException("Hermes excedeu o limite de tempo; o processo filho foi encerrado.");
            }

            var stdout = await stdoutTask;
            _ = await stderrTask;
            if (process.ExitCode != 0)
            {
                var detail = TryReadError(stdout);
                throw new InvalidOperationException(
                    string.IsNullOrWhiteSpace(detail)
                        ? "Hermes Agent falhou no processo isolado."
                        : $"Hermes Agent falhou: {detail}");
            }

            using var document = JsonDocument.Parse(stdout);
            if (!document.RootElement.TryGetProperty("result", out var resultElement) ||
                resultElement.ValueKind != JsonValueKind.String)
                throw new InvalidOperationException("Hermes retornou uma resposta inválida.");

            var result = resultElement.GetString()?.Trim();
            if (string.IsNullOrWhiteSpace(result))
                throw new InvalidOperationException("Hermes Agent retornou uma resposta vazia.");

            return new ModelResponse(
                result.Length > MaxOutputLength ? result[..MaxOutputLength] : result,
                Name,
                model);
        }
        catch (System.ComponentModel.Win32Exception exception)
        {
            throw new InvalidOperationException(
                "Python não foi encontrado. Instale Python 3 e configure ATLAS_HERMES_PYTHON.", exception);
        }
        finally
        {
            if (processStarted && !process.HasExited) TryKill(process);
        }
    }

    private static string BuildTask(ModelRequest request)
    {
        var builder = new StringBuilder();
        if (!string.IsNullOrWhiteSpace(request.SystemInstruction))
            builder.AppendLine(request.SystemInstruction);

        foreach (var message in request.History ?? [])
        {
            if (string.IsNullOrWhiteSpace(message.Content)) continue;
            builder.Append(message.Role.Equals("assistant", StringComparison.OrdinalIgnoreCase)
                ? "Atlas: " : "Usuário: ");
            builder.AppendLine(message.Content.Length > 2_000
                ? message.Content[..2_000] : message.Content);
        }

        builder.Append("Solicitação atual: ").Append(request.Prompt);
        return builder.ToString();
    }

    private static string? TryReadError(string output)
    {
        try
        {
            using var document = JsonDocument.Parse(output);
            return document.RootElement.TryGetProperty("error", out var error)
                ? error.GetString()
                : null;
        }
        catch (JsonException) { return null; }
    }

    private static void TryKill(Process process)
    {
        try { process.Kill(entireProcessTree: true); }
        catch (InvalidOperationException) { }
        catch (System.ComponentModel.Win32Exception) { }
    }
}
