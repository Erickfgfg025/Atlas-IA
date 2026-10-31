using Atlas.Application.Settings;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace Atlas.Desktop.ViewModels;

public partial class MainViewModel(ISettingsStore settingsStore) : ObservableObject
{
    [ObservableProperty]
    private bool enableCloudRequests;

    [ObservableProperty]
    private bool startWithWindows;

    [ObservableProperty]
    private bool keepWindowOnTop;

    [ObservableProperty]
    private string preferredProvider = AtlasSettings.DefaultProvider;

    [ObservableProperty]
    private string statusMessage = "Configurações locais carregadas.";

    public async Task InitializeAsync(CancellationToken cancellationToken = default)
    {
        var settings = await settingsStore.LoadAsync(cancellationToken);
        EnableCloudRequests = settings.EnableCloudRequests;
        StartWithWindows = settings.StartWithWindows;
        KeepWindowOnTop = settings.KeepWindowOnTop;
        PreferredProvider = settings.PreferredProvider;
    }

    [RelayCommand]
    private async Task SaveSettingsAsync(CancellationToken cancellationToken)
    {
        try
        {
            var settings = new AtlasSettings
            {
                EnableCloudRequests = EnableCloudRequests,
                StartWithWindows = StartWithWindows,
                KeepWindowOnTop = KeepWindowOnTop,
                PreferredProvider = PreferredProvider
            };

            await settingsStore.SaveAsync(settings, cancellationToken);
            StatusMessage = "Preferências salvas neste computador.";
        }
        catch (ArgumentException exception)
        {
            StatusMessage = exception.Message;
        }
        catch (IOException)
        {
            StatusMessage = "Não foi possível salvar as preferências. Verifique o acesso à pasta de dados.";
        }
    }
}
