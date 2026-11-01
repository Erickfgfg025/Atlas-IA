using System.Numerics;
using Microsoft.UI.Composition;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Hosting;

namespace Atlas.Desktop.Controls;

/// <summary>
/// GPU/compositor-driven sound wave. Animations continue independently from
/// the UI thread and are stopped whenever the control leaves the visual tree.
/// </summary>
public sealed partial class OrganicOrb : UserControl
{
    private readonly List<Visual> _animatedVisuals = [];

    public OrganicOrb()
    {
        InitializeComponent();
    }

    private void OnLoaded(object sender, RoutedEventArgs e)
    {
        StopAnimations();

        var compositor = ElementCompositionPreview.GetElementVisual(this).Compositor;
        AddWaveAnimation(compositor, BackWave, 0.88f, 1.16f, TimeSpan.FromSeconds(3.8));
        AddWaveAnimation(compositor, MainWave, 0.94f, 1.08f, TimeSpan.FromSeconds(2.7));
        AddWaveAnimation(compositor, FrontWave, 0.82f, 1.22f, TimeSpan.FromSeconds(3.2));
    }

    private void AddWaveAnimation(
        Compositor compositor,
        UIElement element,
        float from,
        float to,
        TimeSpan duration)
    {
        var visual = ElementCompositionPreview.GetElementVisual(element);
        visual.CenterPoint = new Vector3(
            (float)(element.ActualWidth / 2),
            (float)(element.ActualHeight / 2),
            0);
        visual.Scale = Vector3.One;

        var animation = compositor.CreateVector3KeyFrameAnimation();
        animation.InsertKeyFrame(0f, new Vector3(1f, from, 1f));
        animation.InsertKeyFrame(1f, new Vector3(1f, to, 1f));
        animation.Duration = duration;
        animation.Direction = AnimationDirection.Alternate;
        animation.IterationBehavior = AnimationIterationBehavior.Forever;

        visual.StartAnimation(nameof(Visual.Scale), animation);
        _animatedVisuals.Add(visual);
    }

    private void StopAnimations()
    {
        foreach (var visual in _animatedVisuals)
        {
            visual.StopAnimation(nameof(Visual.Scale));
            visual.Scale = Vector3.One;
        }

        _animatedVisuals.Clear();
    }

    private void OnUnloaded(object sender, RoutedEventArgs e) => StopAnimations();
}
