using System.ComponentModel;
using System.Runtime.InteropServices;

namespace Atlas.WindowsBridge;

/// <summary>Small Win32 boundary for toggling the current window's topmost state.</summary>
public static class WindowZOrder
{
    private static readonly nint HwndTopmost = new(-1);
    private static readonly nint HwndNotTopmost = new(-2);
    private const uint SwpNoSize = 0x0001;
    private const uint SwpNoMove = 0x0002;
    private const uint SwpNoActivate = 0x0010;

    [DllImport("user32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool SetWindowPos(
        nint hWnd, nint hWndInsertAfter, int x, int y, int cx, int cy, uint flags);

    public static void SetAlwaysOnTop(nint windowHandle, bool enabled)
    {
        if (windowHandle == nint.Zero)
            throw new ArgumentException("Identificador de janela inválido.", nameof(windowHandle));

        var insertAfter = enabled ? HwndTopmost : HwndNotTopmost;
        if (!SetWindowPos(windowHandle, insertAfter, 0, 0, 0, 0,
                SwpNoMove | SwpNoSize | SwpNoActivate))
            throw new Win32Exception(Marshal.GetLastWin32Error(), "Não foi possível alterar a prioridade da janela.");
    }
}
