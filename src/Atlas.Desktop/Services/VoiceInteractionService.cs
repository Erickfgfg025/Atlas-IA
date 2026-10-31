using Windows.Globalization;
using Windows.Media.Core;
using Windows.Media.Playback;
using Windows.Media.SpeechRecognition;
using Windows.Media.SpeechSynthesis;

namespace Atlas.Desktop.Services;

/// <summary>
/// Windows-native, half-duplex speech loop. Recognition is paused during TTS
/// to prevent the assistant from transcribing its own speaker output.
/// </summary>
public sealed class VoiceInteractionService : IAsyncDisposable
{
    private SpeechRecognizer? _recognizer;
    private readonly SpeechSynthesizer _synthesizer = new();
    private readonly MediaPlayer _player = new();
    private SpeechSynthesisStream? _speechStream;
    private bool _isListening;
    private bool _disposed;

    public event Action<string>? Recognized;
    public event Action<string>? StatusChanged;
    public event Action? PlaybackCompleted;

    public async Task StartListeningAsync(CancellationToken cancellationToken = default)
    {
        ObjectDisposedException.ThrowIf(_disposed, this);
        if (_isListening) return;

        StopSpeech();
        if (_recognizer is null)
        {
            _recognizer = new SpeechRecognizer(new Language("pt-BR"));
            _recognizer.Constraints.Add(new SpeechRecognitionTopicConstraint(
                SpeechRecognitionScenario.Dictation, "atlas_assistant"));
            _recognizer.ContinuousRecognitionSession.ResultGenerated += OnResultGenerated;
            _recognizer.ContinuousRecognitionSession.Completed += OnRecognitionCompleted;

            var compilation = await _recognizer.CompileConstraintsAsync();
            cancellationToken.ThrowIfCancellationRequested();
            if (compilation.Status != SpeechRecognitionResultStatus.Success)
                throw new InvalidOperationException(
                    "O reconhecimento pt-BR não está disponível. Instale o pacote de fala Português (Brasil) no Windows.");
        }

        cancellationToken.ThrowIfCancellationRequested();
        try
        {
            await _recognizer.ContinuousRecognitionSession.StartAsync();
            _isListening = true;
            StatusChanged?.Invoke("Ouvindo");
        }
        catch
        {
            _isListening = false;
            throw;
        }
    }

    public async Task StopListeningAsync()
    {
        if (!_isListening || _recognizer is null) return;
        _isListening = false;
        try
        {
            await _recognizer.ContinuousRecognitionSession.StopAsync();
        }
        catch (InvalidOperationException)
        {
            // The Windows recognition session may have completed between event and stop.
        }
        StatusChanged?.Invoke("Microfone pausado");
    }

    public async Task SpeakAsync(string text, CancellationToken cancellationToken = default)
    {
        ObjectDisposedException.ThrowIf(_disposed, this);
        if (string.IsNullOrWhiteSpace(text)) return;

        StopSpeech();
        StatusChanged?.Invoke("Falando");
        try
        {
            _speechStream = await _synthesizer.SynthesizeTextToStreamAsync(text);
            cancellationToken.ThrowIfCancellationRequested();
            _player.Source = MediaSource.CreateFromStream(_speechStream, _speechStream.ContentType);
            _player.MediaEnded += OnMediaEnded;
            _player.MediaFailed += OnMediaFailed;
            _player.Play();
        }
        catch
        {
            StopSpeech();
            throw;
        }
    }

    public void InterruptSpeech()
    {
        StopSpeech();
        StatusChanged?.Invoke(_isListening ? "Ouvindo" : "Pronto");
    }

    private void OnResultGenerated(
        SpeechContinuousRecognitionSession sender,
        SpeechContinuousRecognitionResultGeneratedEventArgs args)
    {
        if (args.Result.Status != SpeechRecognitionResultStatus.Success ||
            string.IsNullOrWhiteSpace(args.Result.Text))
            return;

        _ = StopListeningFromRecognitionAsync();
        Recognized?.Invoke(args.Result.Text.Trim());
    }

    private async Task StopListeningFromRecognitionAsync()
    {
        try { await StopListeningAsync(); }
        catch (Exception) { StatusChanged?.Invoke("Não foi possível pausar o microfone"); }
    }

    private void OnRecognitionCompleted(
        SpeechContinuousRecognitionSession sender,
        SpeechContinuousRecognitionCompletedEventArgs args)
    {
        _isListening = false;
        if (args.Status != SpeechRecognitionResultStatus.Success)
            StatusChanged?.Invoke("Reconhecimento interrompido");
    }

    private void OnMediaEnded(MediaPlayer sender, object args)
    {
        StopSpeech();
        StatusChanged?.Invoke("Resposta concluída");
        PlaybackCompleted?.Invoke();
    }

    private void OnMediaFailed(MediaPlayer sender, MediaPlayerFailedEventArgs args)
    {
        StopSpeech();
        StatusChanged?.Invoke("Falha na reprodução de áudio");
        PlaybackCompleted?.Invoke();
    }

    private void StopSpeech()
    {
        _player.MediaEnded -= OnMediaEnded;
        _player.MediaFailed -= OnMediaFailed;
        _player.Pause();
        _player.Source = null;
        _speechStream?.Dispose();
        _speechStream = null;
    }

    public async ValueTask DisposeAsync()
    {
        if (_disposed) return;
        _disposed = true;
        if (_recognizer is not null)
        {
            _recognizer.ContinuousRecognitionSession.ResultGenerated -= OnResultGenerated;
            _recognizer.ContinuousRecognitionSession.Completed -= OnRecognitionCompleted;
            if (_isListening)
            {
                try { await _recognizer.ContinuousRecognitionSession.StopAsync(); }
                catch (InvalidOperationException) { }
            }
            _recognizer.Dispose();
        }

        StopSpeech();
        _player.Dispose();
        _synthesizer.Dispose();
    }
}
