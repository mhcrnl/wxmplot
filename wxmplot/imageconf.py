import wx
import wx.lib.agw.flatnotebook as flat_nb
import wx.lib.scrolledpanel as scrolled
import wx.lib.colourselect as csel



from math import log10

import numpy as np

import matplotlib.cm as colormap
from matplotlib.ticker import FuncFormatter

from .colors import register_custom_colormaps, hexcolor, hex2rgb, mpl_color
from .config import bool_ifnotNone, ifnotNone
from .plotconfigframe import FNB_STYLE, autopack
from .utils import  LabeledTextCtrl, SimpleText, Check, Choice, HLine, pack, FloatSpin, MenuItem

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

cm_names = register_custom_colormaps()

ColorMap_List = []

for cm in ('gray', 'coolwarm', 'viridis', 'inferno', 'plasma', 'magma', 'red',
           'green', 'blue', 'magenta', 'yellow', 'cyan', 'Reds', 'Greens',
           'Blues', 'cool', 'hot', 'copper', 'red_heat', 'green_heat',
           'blue_heat', 'spring', 'summer', 'autumn', 'winter', 'ocean',
           'terrain', 'jet', 'stdgamma', 'hsv', 'Accent', 'Spectral', 'PiYG',
           'PRGn', 'Spectral', 'YlGn', 'YlGnBu', 'RdBu', 'RdPu', 'RdYlBu',
           'RdYlGn'):

    if cm in cm_names or hasattr(colormap, cm):
        ColorMap_List.append(cm)


Contrast_List = ['None', '0.01', '0.02', '0.05', '0.1', '0.2', '0.5', '1.0',
                 '2.0', '5.0']

Contrast_NDArray = np.array((-1.0, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1., 2, 5.))

Interp_List = ('nearest', 'bicubic', 'quadric', 'gaussian', 'kaiser',
               'bessel', 'mitchell', 'catrom', 'spline16', 'spline36',
               'bilinear', 'hanning', 'hamming', 'hermite', 'sinc', 'lanczos')

Slices_List = ('None', 'X', 'Y') # , 'Both')

RGB_COLORS = ('red', 'green', 'blue')

class ImageConfig:
    def __init__(self, axes=None, fig=None, canvas=None):
        self.axes   = axes
        self.fig  = fig
        self.canvas  = canvas
        self.cmap  = [colormap.gray, colormap.gray, colormap.gray]
        self.cmap_reverse = False
        self.interp = 'nearest'
        self.show_axis = False
        self.log_scale = False
        self.flip_ud = False
        self.flip_lr = False
        self.rot_level  = 0
        self.contrast_level = 0
        self.datalimits = [None, None, None, None]
        self.cmap_lo = [0, 0, 0]
        self.cmap_range = 1000
        self.cmap_hi = [1000, 1000, 1000]
        self.tricolor_bg = 'black'
        self.tricolor_mode = 'rgb'
        self.int_lo = [0, 0, 0]
        self.int_hi = [1, 1, 1]
        self.data = None
        self.xdata = None
        self.ydata = None
        self.xlab = 'X'
        self.ylab = 'Y'
        self.indices = None
        self.title = 'image'
        self.style = 'image'
        self.highlight_areas = []
        self.ncontour_levels = 10
        self.contour_levels = None
        self.contour_labels = True
        self.cursor_mode = 'zoom'
        self.zoombrush = wx.Brush('#040410',  wx.SOLID)
        self.zoompen   = wx.Pen('#101090',  3, wx.SOLID)
        self.zoom_lims = []
        self.slices = Slices_List[0]
        self.slice_xy = -1, -1
        self.slice_width = 1
        self.slice_onmotion = False
        self.scalebar_show = False
        self.scalebar_showlabel = False
        self.scalebar_label = ''
        self.scalebar_units = 'mm'
        self.scalebar_pos =  5, 5
        self.scalebar_size = 1, 1
        self.scalebar_color = '#EEEE99'
        self.set_formatters()


    def flip_vert(self):
        "flip image along vertical axis (up/down)"
        self.data = np.flipud(self.data)
        if self.ydata is not None:
            self.ydata = self.ydata[::-1]
        self.flip_ud = not self.flip_ud

    def flip_horiz(self):
        "flip image along horizontal axis (left/right)"
        self.data = np.fliplr(self.data)
        if self.xdata is not None:
            self.xdata = self.xdata[::-1]
        self.flip_lr = not self.flip_lr

    def rotate90(self, event=None):
        "rotate 90 degrees, CW"
        if self.xdata is not None:
            self.xdata = self.xdata[::-1]
        if self.ydata is not None:
            self.ydata = self.ydata[:]
        self.xdata, self.ydata = self.ydata, self.xdata
        self.xlab, self.ylab = self.ylab, self.xlab
        self.data = np.rot90(self.data)
        self.rot_level += 1
        if self.rot_level == 4:
            self.rot_level = 0

    def set_formatters(self):
        if self.axes is not None:
            self.axes.xaxis.set_major_formatter(FuncFormatter(self.xformatter))
            self.axes.yaxis.set_major_formatter(FuncFormatter(self.yformatter))

    def xformatter(self, x, pos):
        " x-axis formatter "
        return self._format(x, pos, dtype='x')

    def yformatter(self, y, pos):
        " y-axis formatter "
        return self._format(y, pos, dtype='y')

    def _format(self, x, pos, dtype='x'):
        """ home built tick formatter to use with FuncFormatter():
        x     value to be formatted
        type  'x' or 'y' or 'y2' to set which list of ticks to get

        also sets self._yfmt/self._xfmt for statusbar
        """
        fmt = '%1.5g'
        if dtype == 'y':
            ax = self.axes.yaxis
            dat  = self.ydata
            if dat is None:
                dat = np.arange(self.data.shape[0])
        else:
            ax = self.axes.xaxis
            dat = self.xdata
            if dat is None:
                dat = np.arange(self.data.shape[1])

        ticks = [0,1]
        onep = 1.00001
        try:
            dtick = 0.1 * onep * (dat.max() - dat.min())
        except:
            dtick = 0.2 * onep
        try:
            ticks = ax.get_major_locator()()
        except:
            ticks = [0, 1]
        try:
            dtick = abs(dat[int(ticks[1])] - dat[int(ticks[0])]) * onep
        except:
            pass

        if dtick > 89999:
            fmt = '%.2e'
        else:
            fmt = '%%1.%df' % max(0, -round(log10(0.75*dtick)))

        try:
            s =  fmt % dat[int(x)]
        except:
            s = ''
        s.strip()
        s = s.replace('+', '')
        while s.find('e0')>0:
            s = s.replace('e0','e')
        while s.find('-0')>0:
            s = s.replace('-0','-')
        return s

    def relabel(self):
        " re draw labels (title, x,y labels)"
        pass

    def set_zoombrush(self,color, style):
        self.zoombrush = wx.Brush(color, style)

    def set_zoompen(self,color, style):
        self.zoompen = wx.Pen(color, 3, style)

    def tricolor_white_bg(self, img):
        """transforms image from RGB with (0,0,0)
        showing black to  RGB with 0,0,0 showing white

        takes the Red intensity and sets
        the new intensity to go
        from (0, 0.5, 0.5) (for Red=0)  to (0, 0, 0) (for Red=1)
        and so on for the Green and Blue maps.

        Thus the image will be transformed from
          old intensity                new intensity
          (0.0, 0.0, 0.0) (black)   (1.0, 1.0, 1.0) (white)
          (1.0, 1.0, 1.0) (white)   (0.0, 0.0, 0.0) (black)
          (1.0, 0.0, 0.0) (red)     (1.0, 0.5, 0.5) (red)
          (0.0, 1.0, 0.0) (green)   (0.5, 1.0, 0.5) (green)
          (0.0, 0.0, 1.0) (blue)    (0.5, 0.5, 1.0) (blue)

        """
        tmp = 0.5*(1.0 - (img - img.min())/(img.max() - img.min()))
        out = tmp*0.0
        out[:,:,0] = tmp[:,:,1] + tmp[:,:,2]
        out[:,:,1] = tmp[:,:,0] + tmp[:,:,2]
        out[:,:,2] = tmp[:,:,0] + tmp[:,:,1]
        return out

    def rgb2cmy(self, img, whitebg=False):
        """transforms image from RGB to CMY"""
        tmp = img*1.0
        if whitebg:
            tmp = (1.0 - (img - img.min())/(img.max() - img.min()))
        out = tmp*0.0
        out[:,:,0] = (tmp[:,:,1] + tmp[:,:,2])/2.0
        out[:,:,1] = (tmp[:,:,0] + tmp[:,:,2])/2.0
        out[:,:,2] = (tmp[:,:,0] + tmp[:,:,1])/2.0
        return out

    def set_config(self, interp=None, colormap=None, reverse_colormap=None,
                   contrast_level=None, flip_ud=None, flip_lr=None,
                   rot=None, tricolor_bg=None, ncontour_levels=None,
                   title=None, style=None):
        """set configuration options:

           interp, colormap, reverse_colormap, contrast_levels, flip_ud,
           flip_lr, rot, tricolor_bg, ncontour_levels, title, style
        """
        if interp is not None:
            interp = interp.lower()
            self.interp = interp if interp in Interp_List else self.interp

        if colormap is not None:
            colormap = colormap.lower()
            if colormap.endswith('_r'):
                reverse_colormap = True
                colormap = colormap[:-2]
            self.colormap = colormap if colormap in ColorMap_List else self.colormap

        if contrast_level is not None:
            self.contrast_level = float(contrast_level)

        self.cmap_reverse = bool_ifnotNone(reverse_colormap, self.cmap_reverse)
        self.flip_ud = bool_ifnotNone(flip_ud, self.flip_ud)
        self.flip_lr = bool_ifnotNone(flip_lr, self.flip_lr)
        self.rot     = bool_ifnotNone(rot, self.rot)

        if tricolor_bg is not None:
            tricolor_bg = tricolor_bg.lower()
            if tricolor_bg in ('black', 'white'):
                self.tricolor_bg = tricolor_bg

        if ncontour_levels is not None:
            self.ncontour_level = int(ncontour_levels)

        if style is not None:
            style = style.lower()
            if style in ('image', 'contour'):
                self.style = style

        self.title = ifnotNone(title, self.title)


    def get_config(self):
        """get dictionary of configuration options"""
        out = {'reverse_colormap': self.cmap_reverse}
        for attr in ('interp', 'colormap', 'contrast_levels', 'flip_ud',
                     'flip_lr', 'rot', 'tricolor_bg', 'ncontour_levels',
                     'title', 'style'):
            out[attr] = getattr(self, attr)
        return out

labstyle= wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.ALL

class ImageConfigFrame(wx.Frame):
    """ GUI Configure Frame for Images"""
    def __init__(self, parent=None, config=None, trace_color_callback=None):
        if config is None:
            config = ImageConfig()
        self.conf   = config
        self.parent = parent
        self.canvas = self.conf.canvas
        self.axes = self.canvas.figure.get_axes()
        self.DrawPanel()
        mbar = wx.MenuBar()
        fmenu = wx.Menu()
        MenuItem(self, fmenu, "Save Configuration\tCtrl+S",
                 "Save Configuration",
                 self.save_config)
        MenuItem(self, fmenu, "Load Configuration\tCtrl+R",
                 "Load Configuration",
                 self.load_config)
        mbar.Append(fmenu, 'File')
        self.SetMenuBar(mbar)

    def save_config(self, evt=None, fname='wxmplot.yaml'):
        if not HAS_YAML:
            return
        file_choices = 'YAML Config File (*.yaml)|*.yaml'
        dlg = wx.FileDialog(self, message='Save image configuration',
                            defaultDir=os.getcwd(),
                            defaultFile=fname,
                            wildcard=file_choices,
                            style=wx.FD_SAVE|wx.FD_CHANGE_DIR)

        if dlg.ShowModal() == wx.ID_OK:
            conf = self.conf.get_current_config()
            ppath = os.path.abspath(dlg.GetPath())
            with open(ppath, 'w') as fh:
                fh.write("%s\n" % yaml.dump(conf))


    def load_config(self, evt=None):
        if not HAS_YAML:
            return
        file_choices = 'YAML Config File (*.yaml)|*.yaml'
        dlg = wx.FileDialog(self, message='Read image configuration',
                            defaultDir=os.getcwd(),
                            wildcard=file_choices,
                            style=wx.FD_OPEN)

        if dlg.ShowModal() == wx.ID_OK:
            conf = yaml.safe_load(open(os.path.abspath(dlg.GetPath()), 'r').read())
            self.conf.load_config(conf)

    def DrawPanel(self):
        style = wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, self.parent, -1, 'Configure Image', style=style)

        conf = self.conf
        panel = self
        # scrolled.ScrolledPanel(self, size=(600, 200),
        #                               style=wx.GROW|wx.TAB_TRAVERSAL)
        panel.SetFont(wx.Font(12,wx.SWISS,wx.NORMAL,wx.NORMAL,False))
        panel.SetBackgroundColour(hex2rgb('#FEFEFE'))

        sizer = wx.GridBagSizer(2, 2)
        irow = 0
        bstyle=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.ST_NO_AUTORESIZE


        # contours
        ctitle = SimpleText(panel, 'Contours:', colour='#DD0000')
        label = SimpleText(panel,  "# Levels:")

        self.ncontours = FloatSpin(panel, value=conf.ncontour_levels,
                                     min_val=0, max_val=5000,
                                     increment=1, digits=0, size=(60, -1),
                                     action=self.onContourEvents)

        self.showlabels = Check(panel, label='Show Labels?',
                                default=conf.contour_labels,
                                action=self.onContourEvents)

        sizer.Add(ctitle,          (irow, 0), (1, 2), labstyle, 2)
        irow += 1
        sizer.Add(label,           (irow, 0), (1, 1), labstyle, 2)
        sizer.Add(self.ncontours,  (irow, 1), (1, 1), labstyle, 2)
        sizer.Add(self.showlabels, (irow, 2), (1, 1), labstyle, 2)
        irow += 1
        sizer.Add(HLine(panel, size=(400, -1)), (irow, 0), (1, 3), labstyle, 2)

        # X/Y Slices
        title =  SimpleText(panel, 'X/Y Slices:', colour='#DD0000')
        label_dir = SimpleText(panel, "Direction:")
        label_wid = SimpleText(panel, "Width (pixels):")
        self.slice_width = FloatSpin(panel, value=conf.slice_width,
                                     min_val=0, max_val=5000,
                                     increment=1, digits=0, size=(60, -1),
                                     action=self.onSliceEvents)
        self.slice_dir =  Choice(panel, size=(90, -1),
                                 choices=Slices_List,
                                 action=self.onSliceEvents)
        self.slice_dir.SetStringSelection(conf.slices)

        self.slice_dynamic = Check(panel,label='Slices Follow Mouse Motion?',
                                   default=conf.slice_onmotion,
                                   action=self.onSliceEvents)
        irow += 1
        sizer.Add(title,            (irow, 0), (1, 1), labstyle, 2)
        sizer.Add(self.slice_dynamic, (irow, 1), (1, 2), labstyle, 2)
        irow += 1
        sizer.Add(label_dir,        (irow, 0), (1, 1), labstyle, 2)
        sizer.Add(self.slice_dir,   (irow, 1), (1, 1), labstyle, 2)
        sizer.Add(label_wid,        (irow, 2), (1, 1), labstyle, 2)
        sizer.Add(self.slice_width, (irow, 3), (1, 1), labstyle, 2)

        irow += 1
        sizer.Add(HLine(panel, size=(400, -1)), (irow, 0), (1, 3), labstyle, 2)

        # Scalebar
        ypos, xpos = conf.scalebar_pos
        ysiz, xsiz = conf.scalebar_size
        units = conf.scalebar_units
        dshape = conf.data.shape
        nmax = max(dshape[0], dshape[1])
        xdata = conf.xdata
        ydata = conf.ydata
        xstep, ystep = 1, 1
        if xdata is not None:
            xstep = abs(np.diff(xdata).mean())
        if ydata is not None:
            ystep = abs(np.diff(ydata).mean())


        title =  SimpleText(panel, 'Scalebar:', colour='#DD0000')
        # label_dir = SimpleText(panel, "Direction:")
        # label_wid = SimpleText(panel, "Width (pixels):")

        lab_opts = dict(size=(120, -1))
        color_label = SimpleText(panel, 'Color: ')
        xpos_label = SimpleText(panel, 'X Position: ')
        ypos_label = SimpleText(panel, 'Y Position: ')
        size_label = SimpleText(panel, 'Scalebar Size: ')
        pos_label = SimpleText(panel, "Scalebar Position (pixels from lower left):")
        width_label = SimpleText(panel, 'Width (%s): ' % units)
        height_label = SimpleText(panel, 'Height (pixels): ')

        self.show_scalebar = Check(panel, label='Show Scalebar',
                                   default=conf.scalebar_show,
                                   action=self.onScalebarEvents)

        self.show_label = Check(self, label='Show Label?',
                                default=conf.scalebar_showlabel,
                                action=self.onScalebarEvents)


        stext = "Image Size: X=%d, Y=%d pixels; Pixel Size: X=%13.5g, Y=%13.5g %s"
        stext = stext % (dshape[1], dshape[0], xstep, ystep, units)
        scale_text = SimpleText(panel, label=stext)

        self.label  = LabeledTextCtrl(panel, value=conf.scalebar_label,
                                      size=(150, -1),
                                      labeltext='Label:',
                                      action=self.onScalebarEvents)

        self.color = csel.ColourSelect(panel,  -1, "",
                                       mpl_color(conf.scalebar_color),
                                       size=(50, -1))
        self.color.Bind(csel.EVT_COLOURSELECT, self.onScalebarEvents)



        opts = dict(min_val=0, increment=1, digits=0, size=(100, -1),
                    action=self.onScalebarEvents)

        self.xpos = FloatSpin(panel,  value=xpos, max_val=dshape[1], **opts)
        self.ypos = FloatSpin(panel,  value=ypos, max_val=dshape[0], **opts)
        self.height = FloatSpin(panel, value=ysiz, max_val=dshape[0], **opts)

        opts['increment'] = xstep
        opts['digits'] = max(1, 2 - int(np.log10(abs(xstep))))
        self.width = FloatSpin(panel, value=xsiz, max_val=dshape[1]*xstep, **opts)


        irow += 1
        sizer.Add(title,           (irow, 0), (1, 1), labstyle, 2)
        sizer.Add(scale_text,      (irow, 1), (1, 4), labstyle, 2)


        irow += 1
        sizer.Add(size_label,     (irow, 0), (1, 3), labstyle, 2)

        irow += 1
        sizer.Add(width_label,     (irow, 0), (1, 1), labstyle, 2)
        sizer.Add(self.width,      (irow, 1), (1, 1), labstyle, 2)
        sizer.Add(height_label,    (irow, 2), (1, 1), labstyle, 2)
        sizer.Add(self.height,     (irow, 3), (1, 1), labstyle, 2)

        irow += 1
        sizer.Add(wx.StaticLine(self, -1, size=(275,-1), style=wx.LI_HORIZONTAL),
                  (irow, 0), (1, 2), wx.GROW|labstyle, 2)

        irow += 1
        sizer.Add(pos_label,     (irow, 0), (1, 3), labstyle, 2)

        irow += 1
        sizer.Add(xpos_label,   (irow, 0), (1, 1), labstyle, 2)
        sizer.Add(self.xpos,    (irow, 1), (1, 1), labstyle, 2)
        sizer.Add(ypos_label,   (irow, 2), (1, 1), labstyle, 2)
        sizer.Add(self.ypos,    (irow, 3), (1, 1), labstyle, 2)


        irow += 1
        sizer.Add(HLine(panel, size=(400, -1)), (irow, 0), (1, 3), labstyle, 2)


        irow += 1
        sizer.Add(self.label.label,      (irow, 0), (1, 1), labstyle, 2)
        sizer.Add(self.label,       (irow, 1), (1, 1), labstyle, 2)
        sizer.Add(color_label,     (irow, 2), (1, 1), labstyle, 2)
        sizer.Add(self.color,      (irow, 3), (1, 1), labstyle, 2)

        irow += 1
        sizer.Add(self.show_scalebar,  (irow, 1), (1, 1), labstyle, 2)
        sizer.Add(self.show_label,  (irow, 2), (1, 2), labstyle, 2)

        irow += 1
        sizer.Add(wx.StaticLine(self, -1, size=(275,-1), style=wx.LI_HORIZONTAL),
                  (irow, 0), (1, 2), wx.GROW|labstyle, 2)

        autopack(panel, sizer)

        self.SetMinSize((525, 200))
        self.SetSize((550, 400))
        self.Show()
        self.Raise()


    def onContourEvents(self, event=None):
        self.conf.ncontour_levels = self.ncontours.GetValue()
        self.conf.contour_labels  = self.showlabels.IsChecked()
        self.parent.onContourToggle()

    def onSliceEvents(self, event=None):
        self.conf.slice_width = self.slice_width.GetValue()
        self.conf.slices = self.slice_dir.GetStringSelection()
        self.conf.slice_onmotion = self.slice_dynamic.IsChecked()
        self.parent.onSliceChoice()

    def onScalebarEvents(self, event=None):
        self.conf.scalebar_show = self.show_scalebar.IsChecked()
        self.conf.scalebar_showlabel = self.show_label.IsChecked()
        self.conf.scalebar_label = self.label.GetValue()
        self.conf.scalebar_pos =  self.ypos.GetValue(), self.xpos.GetValue()
        self.conf.scalebar_size = self.height.GetValue(), self.width.GetValue()

        self.conf.scalebar_color = col = hexcolor(self.color.GetValue()[:3])

        self.parent.panel.redraw()
