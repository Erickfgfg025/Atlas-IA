using Atlas.WindowsBridge;

namespace Atlas.UnitTests.Security;

public sealed class SafeWindowsActionsTests
{
    private readonly SafeWindowsActions _actions = new();

    [Theory]
    [InlineData("https://example.com")]
    [InlineData("http://example.com/path?q=1")]
    public void ValidateExternalUri_AcceptsHttpSchemes(string value)
    {
        var uri = _actions.ValidateExternalUri(value, userConfirmed: true);
        Assert.Equal(value, uri.AbsoluteUri);
    }

    [Theory]
    [InlineData("file:///C:/Windows/win.ini")]
    [InlineData("powershell://invoke")]
    [InlineData("javascript:alert(1)")]
    [InlineData("https://user:password@example.com")]
    [InlineData("not a url")]
    public void ValidateExternalUri_RejectsUnsafeSchemesAndCredentials(string value)
    {
        Assert.Throws<ArgumentException>(() => _actions.ValidateExternalUri(value, userConfirmed: true));
    }

    [Fact]
    public void ValidateExternalUri_RequiresExplicitConfirmation()
    {
        Assert.Throws<UnauthorizedAccessException>(
            () => _actions.ValidateExternalUri("https://example.com", userConfirmed: false));
    }
}
