import wx

W, H = 1500, 860
app = wx.App(False)
bmp = wx.Bitmap(W, H)
dc = wx.MemoryDC(bmp)
dc.SetBackground(wx.WHITE_BRUSH)
dc.Clear()
gc = wx.GraphicsContext.Create(dc)
font_b = wx.Font(17, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
font = wx.Font(14, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
POWER, LOGIC, DRIVE = wx.Colour(255, 235, 230), wx.Colour(225, 238, 255), wx.Colour(235, 255, 230)
boxes = {}


def box(key, x, y, w, h, title, sub, fill):
    gc.SetPen(wx.Pen(wx.Colour(60, 60, 60), 2))
    gc.SetBrush(wx.Brush(fill))
    gc.DrawRoundedRectangle(x, y, w, h, 10)
    gc.SetFont(font_b, wx.Colour(20, 20, 20))
    tw, th = gc.GetTextExtent(title)
    gc.DrawText(title, x + (w - tw) / 2, y + 12)
    gc.SetFont(font, wx.Colour(60, 60, 60))
    for i, line in enumerate(sub.replace('|', '\n').split('\n')):
        lw, lh = gc.GetTextExtent(line)
        gc.DrawText(line, x + (w - lw) / 2, y + 44 + i * 24)
    boxes[key] = (x, y, w, h)


def arrow(a, b, label='', color=wx.Colour(200, 40, 40), side='r', dy=0):
    ax, ay, aw, ah = boxes[a]
    bx, by, bw, bh = boxes[b]
    if side == 'r':
        p0, p1 = (ax + aw, ay + ah / 2 + dy), (bx, by + bh / 2 + dy)
    else:
        p0, p1 = (ax + aw / 2 + dy, ay + ah), (bx + bw / 2 + dy, by)
    gc.SetPen(wx.Pen(color, 4))
    gc.StrokeLine(p0[0], p0[1], p1[0], p1[1])
    import math
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    gc.SetBrush(wx.Brush(color))
    pts = [p1, (p1[0] - 16 * math.cos(ang - 0.4), p1[1] - 16 * math.sin(ang - 0.4)),
           (p1[0] - 16 * math.cos(ang + 0.4), p1[1] - 16 * math.sin(ang + 0.4))]
    path = gc.CreatePath(); path.MoveToPoint(*pts[0]); path.AddLineToPoint(*pts[1]); path.AddLineToPoint(*pts[2]); path.CloseSubpath()
    gc.FillPath(path)
    if label:
        gc.SetFont(font, color)
        gc.DrawText(label, (p0[0] + p1[0]) / 2 + 6, (p0[1] + p1[1]) / 2 - 26)


box('vin', 30, 40, 230, 110, 'VIN 12-36 V', 'J3 / J4 screw terminals', POWER)
box('prot', 320, 40, 260, 110, 'Input protection', 'TVS SMBJ36CA|LM74700-Q1 rev. polarity', POWER)
box('efuse', 640, 40, 250, 110, 'eFuse TPS16890', 'UVLO 10.7 V, OCP ~15 A', POWER)
box('shunt', 950, 40, 260, 110, 'DC-bus sense', '5 mOhm + INA240A1', POWER)
box('buck', 1250, 250, 230, 110, 'Buck LMR38020', '+3V3_MCU / +3V3_A', POWER)
box('drv', 640, 470, 250, 130, 'DRV8323RS', 'gate driver, 3x CSA|charge pump', DRIVE)
box('hb', 950, 470, 260, 130, '3x half bridge', 'NTMFS006N08MC|2 mOhm shunts', DRIVE)
box('motor', 1270, 470, 200, 130, 'Motor', 'J5 / J6 / J7|phase A / B / C', DRIVE)
box('mcu', 200, 470, 260, 130, 'ESP32-WROOM-32E', 'Wi-Fi / BLE MCU', LOGIC)
box('can', 30, 700, 250, 110, 'CAN SN65HVD230', 'J8 bus connector', LOGIC)
box('uart', 330, 700, 230, 110, 'UART J1', 'programming / control', LOGIC)
box('temp', 640, 700, 250, 110, 'TMP235', 'board temperature', LOGIC)

arrow('vin', 'prot'); arrow('prot', 'efuse'); arrow('efuse', 'shunt')
arrow('shunt', 'hb', '+VBUS_PROT', side='d')
arrow('shunt', 'buck', side='d', dy=100)
arrow('drv', 'hb', color=wx.Colour(40, 130, 40))
arrow('hb', 'motor', color=wx.Colour(40, 130, 40))
arrow('mcu', 'drv', 'PWM x6, SPI', color=wx.Colour(40, 80, 200), dy=-25)
arrow('mcu', 'can', color=wx.Colour(40, 80, 200), side='d', dy=-60)
arrow('mcu', 'uart', color=wx.Colour(40, 80, 200), side='d', dy=40)
gc.SetFont(font, wx.Colour(40, 80, 200))
gc.DrawText('ADC inputs: phase currents (DRV8323 CSA),', 640, 625)
gc.DrawText('DC-bus current (INA240A1), temperature', 640, 648)
dc.SelectObject(wx.NullBitmap)
bmp.SaveFile('block_diagram.png', wx.BITMAP_TYPE_PNG)
print('saved')
