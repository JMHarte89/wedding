# Export every print/*.docx to a matching print/*.pdf.
#
#     powershell -ExecutionPolicy Bypass -File scripts\make-pdfs.ps1
#
# Run after scripts/build-print.py. Windows + Word only: it drives Word over
# COM so the PDFs come from the same layout engine that paginates the .docx,
# which is what makes the reported page counts trustworthy.
#
# Word runs invisible here, so any modal prompt it raises never appears on
# screen and the COM call simply never returns. Three details avoid that, and
# all three are load-bearing:
#
#   * SaveAs2 with format 17, NOT ExportAsFixedFormat.
#   * WarnBeforeSavingPrintingSendingMarkup must be turned off first.
#   * Read page statistics BEFORE SaveAs2 and close straight after it. Once
#     saved as PDF the document is bound to the new file, and querying
#     ComputeStatistics or PageSetup at that point wedges.
#
# A fresh Word instance per document, disposed as we go. Slower than holding
# one open across the loop, but a single stuck document can't wedge the run.
#
# If a conversion ever does hang, kill it with:  Stop-Process -Name WINWORD -Force

param(
    [string] $PrintDir
)

if (-not $PrintDir) {
    $PrintDir = Join-Path (Split-Path -Parent $PSScriptRoot) 'print'
}
if (-not (Test-Path $PrintDir)) { throw "No print folder at $PrintDir" }

$docs = Get-ChildItem $PrintDir -Filter *.docx | Sort-Object Name
if (-not $docs) { throw "No .docx in $PrintDir - run scripts/build-print.py first" }

foreach ($f in $docs) {
    $target = Join-Path $PrintDir ($f.BaseName + '.pdf')
    if (Test-Path $target) { Remove-Item $target -Force }

    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $word.Options.WarnBeforeSavingPrintingSendingMarkup = $false

    $doc = $word.Documents.Open($f.FullName, $false, $true)
    $doc.Repaginate()
    $pages = $doc.ComputeStatistics(2)
    $setup = $doc.Sections.Item(1).PageSetup
    $w = [math]::Round($setup.PageWidth / 72 * 25.4)
    $h = [math]::Round($setup.PageHeight / 72 * 25.4)
    if ($setup.Orientation -eq 1) { $orient = 'landscape' } else { $orient = 'portrait' }

    $doc.SaveAs2($target, 17)
    $doc.Close($false)
    $word.Quit()

    $kb = [math]::Round((Get-Item $target).Length / 1KB)
    Write-Output ("{0,-22} {1,3} page(s)  {2}x{3}mm {4,-9} {5,6} KB" -f ($f.BaseName + '.pdf'), $pages, $w, $h, $orient, $kb)
}
