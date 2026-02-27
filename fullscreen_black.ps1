Add-Type -AssemblyName System.Windows.Forms,System.Drawing

$form = New-Object System.Windows.Forms.Form
$form.BackColor = [System.Drawing.Color]::Black
$form.FormBorderStyle = 'None'
$form.WindowState = 'Maximized'
$form.TopMost = $true
$form.KeyPreview = $true

# Close on ESC
$form.Add_KeyDown({
    param($sender,$e)
    if ($e.KeyCode -eq [System.Windows.Forms.Keys]::Escape) {
        $sender.Close()
    }
})

# Close on mouse click or double-click
$form.Add_MouseClick({ param($s,$ea) $s.Close() })
$form.Add_MouseDoubleClick({ param($s,$ea) $s.Close() })

[void]$form.ShowDialog()
