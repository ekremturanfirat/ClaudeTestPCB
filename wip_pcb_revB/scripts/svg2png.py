import sys, glob, os, wx, wx.svg
app = wx.App(False)
def render(svgs, out, cols=4, cell=260, label=True):
    rows = (len(svgs)+cols-1)//cols
    W, H = cols*cell, rows*(cell+18)
    bmp = wx.Bitmap(W, H); dc = wx.MemoryDC(bmp); dc.SetBackground(wx.WHITE_BRUSH); dc.Clear()
    gc = wx.GraphicsContext.Create(dc)
    for i, f in enumerate(svgs):
        img = wx.svg.SVGimage.CreateFromFile(f)
        x, y = (i % cols)*cell, (i//cols)*(cell+18)
        b = img.ConvertToScaledBitmap(wx.Size(cell-10, cell-10))
        dc.DrawBitmap(b, x+5, y+5)
        dc.SetTextForeground(wx.BLACK); dc.DrawText(os.path.basename(f)[:34], x+4, y+cell)
    dc.SelectObject(wx.NullBitmap); bmp.SaveFile(out, wx.BITMAP_TYPE_PNG)
if __name__ == '__main__':
    render(sorted(glob.glob(sys.argv[1]+'/*.svg')), sys.argv[2], int(sys.argv[3]) if len(sys.argv)>3 else 4)
