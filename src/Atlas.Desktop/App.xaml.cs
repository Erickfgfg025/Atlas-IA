using Atlas.Infrastructure.Settings;
using Microsoft.UI.Xaml;

namespace Atlas.Desktop;

public partial class App : Microsoft.UI.Xaml.Application
{
    private Window? _window;

    public App()
    {
        InitializeComponent();
    }

    protected override void OnLaunched(LaunchActivatedEventArgs args)
    {
        var settingsStore = new JsonSettingsStore();
        _window = new MainWindow(settingsStore);
        _window.Activate();
    }
}
