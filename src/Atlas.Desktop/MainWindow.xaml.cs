using Atlas.Application.Settings;
using Atlas.Desktop.ViewModels;
using Microsoft.UI.Xaml;

namespace Atlas.Desktop;

public sealed partial class MainWindow : Window
{
    private readonly MainViewModel _viewModel;

    public MainWindow(ISettingsStore settingsStore)
    {
        InitializeComponent();
        Title = "Atlas";
        _viewModel = new MainViewModel(settingsStore);
        RootLayout.DataContext = _viewModel;
        RootLayout.Loaded += MainWindow_Loaded;
    }

    private async void MainWindow_Loaded(object sender, RoutedEventArgs e)
    {
        RootLayout.Loaded -= MainWindow_Loaded;
        try
        {
            await _viewModel.InitializeAsync();
        }
        catch (Exception)
        {
            _viewModel.StatusMessage = "Não foi possível carregar as preferências locais.";
        }
    }
}
