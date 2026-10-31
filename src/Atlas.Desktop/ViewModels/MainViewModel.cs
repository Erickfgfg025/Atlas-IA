using Atlas.Application.Settings;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace Atlas.Desktop.ViewModels;

public partial class MainViewModel(ISettingsStore settingsStore) : ObservableObject
{
    [ObservableProperty]
    public partial bool EnableCloudRequests { get; set; }

    [ObservableProperty]
    public partial bool StartWithWindows { get; set; }

    [ObservableProperty]
    public partial bool KeepWindowOnTop { get; set; }

    [ObservableProperty]
    public partial string PreferredProvider { get; set; } = AtlasSettings.DefaultProvider;

    [ObservableProperty]
    public partial string StatusMessage { get; set; } = "Configurações locais carregadas.";

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
