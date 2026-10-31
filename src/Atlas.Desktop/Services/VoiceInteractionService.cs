using System;
using System.Threading;
using System.Threading.Tasks;
using Windows.Globalization;
using Windows.Media;
using Windows.Media.Core;
using Windows.Media.Playback;
using Windows.Media.SpeechRecognition;
using Windows.Media.SpeechSynthesis;
using Windows.Storage.Streams;

namespace Atlas.Desktop.Services;

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

    public async Task StartListeningAsync(CancellationToken cancellationToken = default)
    {
        ObjectDisposedException.ThrowIf(_disposed, this);
        if (_isListening) return;

        StopSpeech();
        if (_recognizer is null)
        {
            _recognizer = new SpeechRecognizer(new Language("pt-BR"));
            _recognizer.Constraints.Add(
                new SpeechRecognitionTopicConstraint(
                    SpeechRecognitionScenario.Dictation,
                    "atlas_assistant"));
            _recognizer.ContinuousRecognitionSession.ResultGenerated += OnResultGenerated;
            _recognizer.ContinuousRecognitionSession.Completed += OnRecognitionCompleted;

            var compilation = await _recognizer.CompileConstraintsAsync();
            cancellationToken.ThrowIfCancellationRequested();
            if (compilation.Status != SpeechRecognitionResultStatus.Success)
                throw new InvalidOperationException(
                    "O reconhecimento de voz em português não está disponível neste Windows. Instale o pacote de fala Português (Brasil).");
        }

        await _recognizer.ContinuousRecognitionSession.StartAsync();
        _isListening = true;
        StatusChanged?.Invoke("Ouvindo");
    }

    public async Task StopListeningAsync()
    {
        if (!_isListening || _recognizer is null) return;
        _isListening = false;
        await _recognizer.ContinuousRecognitionSession.StopAsync();
        StatusChanged?.Invoke("Microfone pausado");
    }

    public async Task SpeakAsync(string text, CancellationToken cancellationToken = default)
    {
        ObjectDisposedException.ThrowIf(_disposed, this);
        if (string.IsNullOrWhiteSpace(text)) return;

        StopSpeech();
        StatusChanged?.Invoke("Falando");
        _speechStream = await _synthesizer.SynthesizeTextToStreamAsync(text);
        cancellationToken.ThrowIfCancellationRequested();
        _player.Source = MediaSource.CreateFromStream(_speechStream, _speechStream.ContentType);
        _player.MediaEnded += OnMediaEnded;
        _player.Play();
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

        StopSpeech();
        Recognized?.Invoke(args.Result.Text.Trim());
    }

    private void OnRecognitionCompleted(
        SpeechContinuousRecognitionSession sender,
        SpeechContinuousRecognitionCompletedEventArgs args)
    {
        if (!_isListening) return;
        _isListening = false;
        StatusChanged?.Invoke(args.Status == SpeechRecognitionResultStatus.Success
            ? "Microfone pausado"
            : "Reconhecimento interrompido");
    }

    private void OnMediaEnded(MediaPlayer sender, object args)
    {
        StopSpeech();
        StatusChanged?.Invoke(_isListening ? "Ouvindo" : "Pronto");
    }

    private void StopSpeech()
    {
        _player.MediaEnded -= OnMediaEnded;
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

        _player.MediaEnded -= OnMediaEnded;
        StopSpeech();
        _player.Dispose();
        _synthesizer.Dispose();
    }
}
