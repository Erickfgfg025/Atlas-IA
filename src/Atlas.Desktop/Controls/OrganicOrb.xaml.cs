using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Media;
using Microsoft.UI.Xaml.Media.Animation;

namespace Atlas.Desktop.Controls;

public sealed partial class OrganicOrb : UserControl
{
    private Storyboard? _storyboard;

    public OrganicOrb()
    {
        InitializeComponent();
    }

    private void OnLoaded(object sender, RoutedEventArgs e)
    {
        if (_storyboard is not null)
        {
            _storyboard.Begin();
            return;
        }

        _storyboard = new Storyboard();
        AddWaveAnimation(_storyboard, BackWaveScale, 0.88, 1.16, 3.8);
        AddWaveAnimation(_storyboard, MainWaveScale, 0.94, 1.08, 2.7);
        AddWaveAnimation(_storyboard, FrontWaveScale, 0.82, 1.22, 3.2);
        _storyboard.Begin();
    }

    private static void AddWaveAnimation(
        Storyboard storyboard,
        ScaleTransform transform,
        double from,
        double to,
        double seconds)
    {
        var animation = new DoubleAnimation
        {
            From = from,
            To = to,
            Duration = new Duration(TimeSpan.FromSeconds(seconds)),
            AutoReverse = true,
            RepeatBehavior = RepeatBehavior.Forever,
            EnableDependentAnimation = true
        };

        Storyboard.SetTarget(animation, transform);
        Storyboard.SetTargetProperty(animation, "ScaleY");
        storyboard.Children.Add(animation);
    }

    private void OnUnloaded(object sender, RoutedEventArgs e)
    {
        _storyboard?.Stop();
    }
}
