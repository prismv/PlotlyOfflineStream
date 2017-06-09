# -*- coding: utf-8 -*-
"""

Plotly offline streaming through ipywidgets

Hsiou-Yuan Liu   hyliu@berkeley.edu
Apr 15, 2017 
"""
from __future__ import division, print_function, with_statement
import plotly.offline as py
import IPython.display
import ipywidgets
from traitlets import Unicode

class UpdaterJS(ipywidgets.HTML): # a widget that has a JavaScript as its content
    _view_module = Unicode("widget-dynamicJS-exec").tag(sync=True)
    _view_name = Unicode("HelloView").tag(sync=True)
    value = Unicode("").tag(sync=True)

class JupyterNotebookPlotlyStream:

    config_default = dict(
        show_link=False,
        link_text='Export to plot.ly',
        validate=True,
        default_width=800,
        default_height=600,
        global_requirejs=True,
    )

    def __init__(self):
        initialized = getattr(py.offline, '__PLOTLY_OFFLINE_INITIALIZED') # due to name mangling...
        if not initialized:
            raise RuntimeError('\n'.join([
                'Plotly Offline mode requires an initialization.',
                'Run the following at the start of a Jupyter notebook:',
                '    import plotly',
                '    plotly.offline.init_notebook_mode()']))
        self._fig = None
        self._opt_html_table_side = None
        self._div_id = None
        self._already_plotted = False
        self.config = self.config_default.copy()
        ## Register interactive JS functions
        # This code is short so being registered multiple times does not hurt
        obj = IPython.display.Javascript(
            'require.undef("widget-dynamicJS-exec");'
            'define("widget-dynamicJS-exec", ["jupyter-js-widgets"], function(widget){'
                'var HelloView = widget.DOMWidgetView.extend({'
                    'render: function(){'
                        'this.pagetitle = document.createElement("div");'
                        'this.pagetitle.appendChild(document.createElement("div"));' # dummy child, needed because update() removes a child
                        'this.el.appendChild(this.pagetitle);'
                    '},'
                    'update: function(){'
                        'var container = this.pagetitle;'
                        'container.removeChild(container.childNodes[0]);'

                        'var child = document.createElement("script");'
                        'child.setAttribute("type", "text/javascript");'
                        'child.textContent = this.model.get("value");'
                        'container.appendChild(child);'
                    '}'
                '});'
                'return {HelloView: HelloView}'
            '})'
        )
        self._obj = obj

    def _plot_html(self):
        return py.offline._plot_html(self._fig, **self.config)

    def setToPlotInNewCell(self):
        """reset the flags for plotting in a new notebook cell

        Note that the contents of logs are not reset(!)
        """
        self._already_plotted = False
        self._div_id = None

    @staticmethod
    def _build_table(left, right, header=''):
        width = '100%'
        if header: # could be extended to 2 entries per column
            #header = "<th>{}</th><th>{}</th>".format(header[0], header[1])
            header = "<thead>{}</thead>".format(header)
        html = ['<center>',
                '<table style="width:{}"><tr>'.format(width),
                header,
                "</tr><tbody><tr><td>",
                '<div id="plotlyStreamTableLeft">',
                left,
                "</div>",
                "</td><td>",
                '<div id="plotlyStreamTableRight">',
                right,
                "</div>",
                "</td></tr></tbody></table>",
                '</center>']
        return ''.join(html)

    def firstRun(self,
                 fig=None,
                 other_content=None,
                 table_header='',
                 table_fig_side='L',
                 html_join=None,
                 show=False):
        if html_join is None:
            self.html_join = lambda html: html
        else:
            self.html_join = html_join
        if fig is None:
            assert self._fig is not None
        else:
            self._fig = fig
        self._other_content = other_content
        self._other_header = table_header
        if self._other_content:
            self._other_side = 'R' if table_fig_side == 'L' else 'L'
            self._fig_side = table_fig_side
        else:
            self._fig_side = None
            self._other_side = None

        self._handle_obj = None
        self._handle_html = None
        self._widget_JS = None
        self._handle_js = None

        ## iplot alternative
        plot_html, plotdivid, _, _ = self._plot_html()

        ## Update
        if self._other_content is not None:
            if self._fig_side == 'L':
                left, right = plot_html, self._other_content
            else:
                right, left = plot_html, self._other_content
            plot_html = self._build_table(left, right, table_header)

        self._html = html_join(plot_html)
        self._html_obj = None
        if show:
            self.show()

        self._div_id = str(plotdivid)
        self._already_plotted = True

    def show(self):
        IPython.display.clear_output()
        #if self._widget_JS is None:
        self._widget_JS = UpdaterJS()
        self._handle_obj = IPython.display.display(self._obj)
        #plot_html, plotdivid, _, _ = self._plot_html()
        #self._html = plot_html
        if self._html:
            ## Display the widget
            if True: #self._handle_html is None:
                #self._handle_js = IPython.display.display(self._widget_JS, display_id='plotlyStream_js')
                self._handle_html = IPython.display.display(self._widget_JS,
                                                            IPython.display.HTML(self._html),
                                                            display_id='plotlyStream_html')
            else:
                self._handle_html.update(IPython.display.display(self._widget_JS, self._html))
                #self._handle_js.update(self._widget_JS)

    def _update(self, n_parse_char):
        ## iplot alternative
        _plot_html, plotdivid, _, _ = self._plot_html()
        #self._html = plot_html = self.html_join(_plot_html)
        plot_html = _plot_html

        ## Process the html text to obtain JS
        # assuming n_parse_char contains all the headers that I want to get rid of
        # The reason to use n_parse_char is that plot_html can be extremely long
        cut_head = plot_html[:n_parse_char].split('<script type="text/javascript">')[-1]
        cut_head += plot_html[n_parse_char:]
        plot_js = cut_head[:-9] # get rid of ending 9 characters "</script>" at the end (without quotations)
        segs = plot_js[:n_parse_char].split(str(plotdivid))
        return plotdivid, self._div_id.join(segs) + plot_js[n_parse_char:]

    def update(self, n_parse_char=1024):
        assert self._fig is not None
        assert self._div_id is not None
        assert self._already_plotted == True

        plotdivid, plot_js = self._update(n_parse_char)

        ## Update
        self._widget_JS.value = plot_js
        #self._div_id = str(plotdivid)
