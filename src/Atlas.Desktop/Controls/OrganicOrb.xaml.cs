using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Media.Animation;

namespace Atlas.Desktop.Controls;

public sealed partial class OrganicOrb : UserControl
{
    public OrganicOrb()
    {
        InitializeComponent();
    }

    private void OnLoaded(object sender, RoutedEventArgs e)
    {
        var animation = new DoubleAnimation
        {
            From = 0.96,
            To = 1.04,
            Duration = new Duration(TimeSpan.FromSeconds(2.8)),
            AutoReverse = true,
            RepeatBehavior = RepeatBehavior.Forever,
            EnableDependentAnimation = true
        };
        Storyboard.SetTarget(animation, GlowScale);
        Storyboard.SetTargetProperty(animation, "ScaleX");
        var yAnimation = new DoubleAnimation
        {
            From = 0.96,
            To = 1.04,
            Duration = new Duration(TimeSpan.FromSeconds(3.2)),
            AutoReverse = true,
            RepeatBehavior = RepeatBehavior.Forever,
            EnableDependentAnimation = true
        };
        Storyboard.SetTarget(yAnimation, GlowScale);
        Storyboard.SetTargetProperty(yAnimation, "ScaleY");
        var storyboard = new Storyboard();
        storyboard.Children.Add(animation);
        storyboard.Children.Add(yAnimation);
        storyboard.Begin();
    }
}
