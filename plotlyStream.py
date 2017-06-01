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
                "<table style='width:{}'><tr>".format(width),
                header,
                "</tr><tbody><tr><td>",
                left,
                "</td><td>",
                right,
                "</td></tr></tbody></table>",
                '</center>']
        return ''.join(html)


    def firstRun(self,
                 fig=None,
                 opt_html_table_side=None,
                 table_header='',
                 table_fig_side='L'):
        if fig is None:
            assert self._fig is not None
        else:
            self._fig = fig
        if table_header is not None:
            self._opt_html_table_side = opt_html_table_side

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
        IPython.display.display(obj)

        ## Display the widget 
        self._widget_JS = UpdaterJS()
        IPython.display.display(self._widget_JS)

        ## iplot alternative
        plot_html, plotdivid, _, _ = self._plot_html()

        ## Update
        if self._opt_html_table_side is not None:
            if table_fig_side == 'L':
                left, right = plot_html, self._opt_html_table_side
            else:
                right, left = plot_html, self._opt_html_table_side
            plot_html = self._build_table(left, right, table_header)

        IPython.display.display(IPython.display.HTML(plot_html))

        self._div_id = str(plotdivid)
        self._already_plotted = True

    def update(self, n_parse_char=1024):
        assert self._fig is not None
        assert self._div_id is not None
        assert self._already_plotted == True

        ## iplot alternative
        plot_html, plotdivid, _, _ = self._plot_html()

        ## Process the html text to obtain JS
        # assuming n_parse_char contains all the headers that I want to get rid of
        # The reason to use n_parse_char is that plot_html can be extremely long
        cut_head = plot_html[:n_parse_char].split('<script type="text/javascript">')[-1]
        cut_head += plot_html[n_parse_char:]
        plot_js = cut_head[:-9] # get rid of ending 9 characters "</script>" at the end (without quotations)
        segs = plot_js[:n_parse_char].split(str(plotdivid))
        plot_js = self._div_id.join(segs) + plot_js[n_parse_char:]

        ## Update
        self._widget_JS.value = plot_js
