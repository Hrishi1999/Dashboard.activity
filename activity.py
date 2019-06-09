# Copyright 2019 Hrishi Patel
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

# noqa: E402

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, Pango, GObject
import logging

from gettext import gettext as _

from sugar3.activity import activity
from sugar3.activity.activity import launch_bundle
from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.graphics.icon import CellRendererIcon
from sugar3.graphics import style
from sugar3.activity.widgets import ActivityButton
from sugar3.activity.widgets import StopButton
from sugar3.datastore import datastore
from sugar3 import profile

from jarabe.model import bundleregistry
from jarabe.journal import misc

from charts import Chart
from readers import JournalReader

import utils
import datetime
import locale

# logging
_logger = logging.getLogger('dashboard-activity')
_logger.setLevel(logging.DEBUG)
logging.basicConfig()

COLOR1 = utils.get_user_fill_color('str')


class DashboardActivity(activity.Activity):

    def __init__(self, handle):

        activity.Activity.__init__(self, handle)

        self.current_chart = None
        self.x_label = ""
        self.y_label = ""
        self.chart_color = utils.get_user_fill_color('str')
        self.chart_line_color = utils.get_user_stroke_color('str')
        self.chart_data = []

        # toolbar with the new toolbar redesign
        toolbar_box = ToolbarBox()

        activity_button = ActivityButton(self)
        toolbar_box.toolbar.insert(activity_button, 0)
        activity_button.show()

        separator = Gtk.SeparatorToolItem()
        separator.props.draw = False
        separator.set_expand(True)
        toolbar_box.toolbar.insert(separator, -1)
        separator.show()

        stop_button = StopButton(self)
        toolbar_box.toolbar.insert(stop_button, -1)
        stop_button.show()

        self.set_toolbar_box(toolbar_box)
        toolbar_box.show()

        # ScrolledWindow as the main container
        scrolled_window_main = Gtk.ScrolledWindow()
        scrolled_window_main.set_can_focus(False)
        scrolled_window_main.set_policy(Gtk.PolicyType.AUTOMATIC,
                                        Gtk.PolicyType.AUTOMATIC)
        scrolled_window_main.set_shadow_type(Gtk.ShadowType.NONE)
        scrolled_window_main.show()
        self.set_canvas(scrolled_window_main)

        frame = Gtk.Frame()
        scrolled_window_main.add(frame)
        frame.show()
        grid = Gtk.Grid(column_spacing=6, row_spacing=3.5)
        grid.set_border_width(20)
        grid.set_halign(Gtk.Align.CENTER)
        frame.add(grid)

        vbox_total_activities = Gtk.VBox()
        vbox_journal_entries = Gtk.VBox()
        vbox_total_contribs = Gtk.VBox()
        hbox_heatmap = Gtk.VBox()

        # VBoxes for total activities, journal entries and total files
        vbox_total_activities.override_background_color(Gtk.StateFlags.NORMAL,
                                                        Gdk.RGBA(1, 1, 1, 1))
        vbox_journal_entries.override_background_color(Gtk.StateFlags.NORMAL,
                                                       Gdk.RGBA(1, 1, 1, 1))
        vbox_total_contribs.override_background_color(Gtk.StateFlags.NORMAL,
                                                      Gdk.RGBA(1, 1, 1, 1))
        hbox_heatmap.override_background_color(Gtk.StateFlags.NORMAL,
                                               Gdk.RGBA(1, 1, 1, 1))

        vbox_tree = Gtk.VBox()
        vbox_tree.override_background_color(Gtk.StateFlags.NORMAL,
                                            Gdk.RGBA(1, 1, 1, 1))

        self.vbox_pie = Gtk.VBox()
        self.vbox_pie.override_background_color(Gtk.StateFlags.NORMAL,
                                                Gdk.RGBA(1, 1, 1, 1))

        label_dashboard = Gtk.Label()
        text_dashboard = "<b>{0}</b>".format(_("Dashboard"))
        label_dashboard.set_markup(text_dashboard)

        # label for total activities
        label_TA = Gtk.Label()
        text_TA = "<b>{0}</b>".format(_("Activities Installed"))
        label_TA.set_markup(text_TA)
        vbox_total_activities.add(label_TA)

        label_total_activities = Gtk.Label()
        vbox_total_activities.add(label_total_activities)

        # label for total journal entries
        label_JE = Gtk.Label()
        text_JE = "<b>{0}</b>".format(_("Journal Entries"))
        label_JE.set_markup(text_JE)
        vbox_journal_entries.add(label_JE)

        label_journal_entries = Gtk.Label()
        vbox_journal_entries.add(label_journal_entries)

        # label for files
        label_CE = Gtk.Label()
        text_CE = "<b>{0}</b>".format(_("Total Files"))
        label_CE.set_markup(text_CE)
        vbox_total_contribs.add(label_CE)

        # label for pie
        label_PIE = Gtk.Label()
        text_PIE = "<b>{0}</b>".format(_("Most used activities"))
        label_PIE.set_markup(text_PIE)
        self.vbox_pie.pack_start(label_PIE, False, True, 5)

        label_contribs = Gtk.Label()
        vbox_total_contribs.add(label_contribs)

        # pie chart
        self.labels_and_values = ChartData(self)
        self.labels_and_values.connect("label-changed", self._label_changed)
        self.labels_and_values.connect("value-changed", self._value_changed)

        eventbox = Gtk.EventBox()
        self.charts_area = ChartArea(self)
        self.charts_area.connect('size_allocate', self._chart_size_allocate)
        eventbox.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("white"))
        eventbox.add(self.charts_area)
        self.vbox_pie.pack_start(eventbox, True, True, 0)

        reader = JournalReader()
        self._graph_from_reader(reader)
        self.current_chart = Chart("pie")
        self.update_chart()

        # font
        font_main = Pango.FontDescription("Granada 14")
        label_JE.modify_font(font_main)
        label_CE.modify_font(font_main)
        label_TA.modify_font(font_main)

        font_actual = Pango.FontDescription("12")
        label_journal_entries.modify_font(font_actual)
        label_total_activities.modify_font(font_actual)
        label_contribs.modify_font(font_actual)
        label_dashboard.modify_font(font_actual)

        # get total number of activities
        registry = bundleregistry.get_registry()
        dsobjects, journal_entries = datastore.find({})

        mime_types = ['image/bmp', 'image/gif', 'image/jpeg',
                      'image/png', 'image/tiff', 'application/pdf',
                      'application/vnd.olpc-sugar',
                      'application/rtf', 'text/rtf',
                      'application/epub+zip', 'text/html',
                      'application/x-pdf']

        self.treeview_list = []
        self.files_list = []
        self.old_list = []
        self.heatmap_list = []

        # to check journal entries which are only a file
        for dsobject in dsobjects:
            new = []
            new.append(dsobject.metadata['title'])
            new.append(misc.get_icon_name(dsobject.metadata))
            new.append(dsobject.metadata['activity_id'])
            new.append(profile.get_color())
            new.append(dsobject.get_object_id())
            new.append(dsobject.metadata)
            new.append(misc.get_date(dsobject.metadata))
            new.append(dsobject.metadata['mtime'])
            self.treeview_list.append(new)
            self.old_list.append(new)

            if dsobject.metadata['mime_type'] in mime_types:
                new2 = []
                new2.append(dsobject.metadata['title'])
                new2.append(misc.get_icon_name(dsobject.metadata))
                new2.append(dsobject.metadata['activity_id'])
                new2.append(profile.get_color())
                new2.append(dsobject.get_object_id())
                new2.append(dsobject.metadata)
                new2.append(misc.get_date(dsobject.metadata))
                new2.append(dsobject.metadata['mtime'])
                self.files_list.append(new2)

            self.old_list = sorted(self.old_list, key=lambda x: x[7])

        # treeview for Journal entries
        self.liststore = Gtk.ListStore(str, str, str, object, str,
                                       datastore.DSMetadata, str, str)
        self.treeview = Gtk.TreeView(self.liststore)
        self.treeview.set_headers_visible(False)

        for i, col_title in enumerate(["Recently Opened Activities"]):

            renderer_title = Gtk.CellRendererText()
            icon_renderer = CellRendererActivityIcon()
            renderer_time = Gtk.CellRendererText()

            renderer_title.set_property('ellipsize', Pango.EllipsizeMode.END)
            renderer_title.set_property('ellipsize-set', True)

            column1 = Gtk.TreeViewColumn("Icon", icon_renderer, text=0)
            column1.add_attribute(icon_renderer, 'file-name',
                                  1)
            column1.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
            column1.add_attribute(icon_renderer, 'xo-color',
                                  3)
            column2 = Gtk.TreeViewColumn(col_title, renderer_title, text=0)
            column2.set_min_width(200)
            column3 = Gtk.TreeViewColumn(col_title, renderer_time, text=6)

            self.treeview.set_tooltip_column(0)
            self.treeview.append_column(column1)
            self.treeview.append_column(column2)
            self.treeview.append_column(column3)

        # combobox for sort selection
        cbox_store = Gtk.ListStore(str)
        cbox_entries = ["All", "Files", "Oldest"]

        for item in cbox_entries:
            cbox_store.append([item])

        combobox = Gtk.ComboBox.new_with_model(cbox_store)
        combobox.connect("changed", self._on_name_combo_changed)
        renderer_text = Gtk.CellRendererText()
        combobox.pack_start(renderer_text, True)
        combobox.add_attribute(renderer_text, "text", 0)
        combobox.set_active(0)

        self._add_to_treeview(self.treeview_list)

        selected_row = self.treeview.get_selection()
        selected_row.connect("changed", self._item_select_cb)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_can_focus(False)
        scrolled_window.set_policy(Gtk.PolicyType.NEVER,
                                   Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_shadow_type(Gtk.ShadowType.NONE)
        scrolled_window.show()

        hbox_tree2 = Gtk.HBox()
        text_treeview = " {0} ".format(_("Journal Entries"))
        self.label_treeview = Gtk.Label(text_treeview)
        hbox_tree2.pack_start(self.label_treeview, False, True, 0)
        hbox_tree2.pack_start(combobox, True, True, 0)

        vbox_tree.pack_start(hbox_tree2, False, False, 5)
        scrolled_window.add(self.treeview)

        # label for recent activities
        label_rec = Gtk.Label(expand=False)
        text_treeview = "{0}".format(_("Recently Opened Activities"))
        label_rec.set_markup(text_treeview)

        vbox_tree.add(scrolled_window)

        label_total_activities.set_text(str(len(registry)))
        label_journal_entries.set_text(str(journal_entries))
        label_contribs.set_text(str(len(self.files_list)))

        # heatmap
        label_heatmap = Gtk.Label(_("User Activity"))
        grid_heatmap = Gtk.Grid(column_spacing=3, row_spacing=2)
        grid_heatmap.set_halign(Gtk.Align.CENTER)
        hbox_heatmap.pack_start(label_heatmap, False, True, 5)
        hbox_heatmap.pack_start(grid_heatmap, False, True, 5)

        self.dates, self.dates_a = self._generate_dates()
        self._build_heatmap(grid_heatmap, self.dates, self.dates_a)

        self.heatmap_liststore = Gtk.ListStore(str, str, str, object, str,
                                               datastore.DSMetadata, str, str)
        heatmap_treeview = Gtk.TreeView(self.heatmap_liststore)
        heatmap_treeview.set_headers_visible(False)

        for i, col_title in enumerate(["Activity"]):

            renderer_title = Gtk.CellRendererText()
            icon_renderer = CellRendererActivityIcon()
            renderer_time = Gtk.CellRendererText()

            column1 = Gtk.TreeViewColumn("Icon", icon_renderer, text=0)
            column1.add_attribute(icon_renderer, 'file-name',
                                  1)
            column1.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
            column1.add_attribute(icon_renderer, 'xo-color',
                                  3)
            column2 = Gtk.TreeViewColumn(col_title, renderer_title, text=0)
            column3 = Gtk.TreeViewColumn(col_title, renderer_time, text=6)

            heatmap_treeview.append_column(column1)
            heatmap_treeview.append_column(column2)
            heatmap_treeview.append_column(column3)

        hbox_heatmap.pack_start(heatmap_treeview, False, True, 5)

        selected_row_heatmap = heatmap_treeview.get_selection()
        selected_row_heatmap.connect("changed", self._item_select_cb)

        # add views to grid
        grid.attach(label_dashboard, 1, 2, 20, 20)
        grid.attach_next_to(vbox_total_activities, label_dashboard,
                            Gtk.PositionType.BOTTOM, 50, 35)
        grid.attach_next_to(vbox_journal_entries, vbox_total_activities,
                            Gtk.PositionType.RIGHT, 50, 35)
        grid.attach_next_to(vbox_total_contribs, vbox_journal_entries,
                            Gtk.PositionType.RIGHT, 50, 35)
        grid.attach_next_to(vbox_tree, vbox_total_activities,
                            Gtk.PositionType.BOTTOM, 75, 90)
        grid.attach_next_to(self.vbox_pie, vbox_tree,
                            Gtk.PositionType.RIGHT, 75, 90)
        grid.attach_next_to(hbox_heatmap, vbox_tree,
                            Gtk.PositionType.BOTTOM, 150, 75)
        grid.show_all()

    def _build_heatmap(self, grid, dates, dates_a):
        j = 1
        k = 1
        counter_days = 0
        counter_weeks = 0
        week_list = [0, 5, 9, 13, 18, 22, 26, 31, 35, 39, 44, 49]

        for i in range(0, 365):
            if (i % 7 == 0):
                j = j + 1
                k = 0
            k = k + 1
            count = 0
            for x in range(0, len(self.old_list)):
                date = self.old_list[x][7][:-16]
                if date == dates[i]:
                    count = count + 1
            box = HeatMapBlock(dates_a[i], count, i)
            box.connect('on-clicked', self._on_clicked_cb)
            lab_days = Gtk.Label()
            lab_months = Gtk.Label()

            # for weekdays
            if(k % 2 == 0 and counter_days < 3):
                day = ''
                if(counter_days == 0):
                    day = dates_a[8][:-13]
                    lab_days.set_text(_(day))
                if(counter_days == 1):
                    day = dates_a[10][:-13]
                    lab_days.set_text(_(day))
                if(counter_days == 2):
                    day = dates_a[12][:-13]
                    lab_days.set_text(_(day))

                grid.attach(lab_days, 0, k, 1, 1)
                counter_days = counter_days + 1

            # for months
            if(k % 4 == 0 and counter_weeks < 54):
                if(counter_weeks == 0):
                    lab_months.set_text(_("Jan"))
                if(counter_weeks == 5):
                    lab_months.set_text(_("Feb"))
                if(counter_weeks == 9):
                    lab_months.set_text(_("Mar"))
                if(counter_weeks == 13):
                    lab_months.set_text(_("Apr"))
                if(counter_weeks == 18):
                    lab_months.set_text(_("May"))
                if(counter_weeks == 22):
                    lab_months.set_text(_("Jun"))
                if(counter_weeks == 26):
                    lab_months.set_text(_("Jul"))
                if(counter_weeks == 31):
                    lab_months.set_text(_("Aug"))
                if(counter_weeks == 35):
                    lab_months.set_text(_("Sep"))
                if(counter_weeks == 39):
                    lab_months.set_text(_("Oct"))
                if(counter_weeks == 44):
                    lab_months.set_text(_("Nov"))
                if(counter_weeks == 49):
                    lab_months.set_text(_("Dec"))

                if counter_weeks in week_list:
                    grid.attach(lab_months, j, 0, 2, 1)

                counter_weeks = counter_weeks + 1

            grid.attach(box, j, k, 1, 1)

    def _on_clicked_cb(self, i, index):
        self.heatmap_liststore.clear()
        del self.heatmap_list[:]

        for y in range(0, len(self.old_list)):
            date = self.old_list[y][7][:-16]
            if date == self.dates[index]:
                self.heatmap_list.append(self.old_list[y])

        for item in self.heatmap_list:
            self.heatmap_liststore.append(item)

    def _generate_dates(self):
        year = datetime.date.today().year

        dt = datetime.datetime(year, 1, 1)
        end = datetime.datetime(year, 12, 31, 23, 59, 59)
        step = datetime.timedelta(days=1)

        result = []
        result_a = []
        while dt < end:
            result_a.append(dt.strftime('%a, %b %d %Y'))
            result.append(dt.strftime('%Y-%m-%d'))
            dt += step
        return result, result_a

    def _add_to_treeview(self, tlist):
        self.liststore.clear()
        for item in tlist:
            self.liststore.append(item)

    def _on_name_combo_changed(self, combo):
        tree_iter = combo.get_active_iter()
        if tree_iter is not None:
            model = combo.get_model()
            selected_item = model[tree_iter][0]
            if selected_item == "Files":
                self._add_to_treeview(self.files_list)
            elif selected_item == "All":
                self._add_to_treeview(self.treeview_list)
            elif selected_item == "Oldest":
                self._add_to_treeview(self.old_list)

    def _item_select_cb(self, selection):
        model, row = selection.get_selected()

        if row is not None:
            metadata = model[row][5]
            bundle_id = metadata.get('activity', '')
            launch_bundle(bundle_id, model[row][4])

    def _chart_size_allocate(self, widget, allocation):
        self._render_chart()

    def _render_chart(self):
        if self.current_chart is None or self.charts_area is None:
            return
        try:
            # Resize the chart for all the screen sizes
            alloc = self.vbox_pie.get_allocation()
            new_width = alloc.width
            new_height = alloc.height

            self.current_chart.width = new_width
            self.current_chart.height = new_height

            # Set options
            self.current_chart.set_color_scheme(color=self.chart_color)
            self.current_chart.set_line_color(self.chart_line_color)

            if self.current_chart.type == "pie":
                self.current_chart.render(self)
            else:
                self.current_chart.render()
            self.charts_area.queue_draw()

        except (ZeroDivisionError, ValueError):
            pass

        return False

    def _graph_from_reader(self, reader):
        self.labels_and_values.model.clear()
        self.chart_data = []

        chart_data = reader.get_chart_data()

        # Load the data
        for row in chart_data:
            self._add_value(None,
                            label=row[0], value=float(row[1]))

            self.update_chart()

    def _add_value(self, widget, label="", value="0.0"):
        data = (label, float(value))
        if data not in self.chart_data:
            pos = self.labels_and_values.add_value(label, value)
            self.chart_data.insert(pos, data)
            self._update_chart_data()

    def update_chart(self):
        if self.current_chart:
            self.current_chart.data_set(self.chart_data)
            self.current_chart.set_x_label(self.x_label)
            self.current_chart.set_y_label(self.y_label)
            self._render_chart()

    def _update_chart_data(self):
        if self.current_chart is None:
            return
        self.current_chart.data_set(self.chart_data)
        self._update_chart_labels()

    def _update_chart_labels(self, title=""):
        if self.current_chart is None:
            return
        self.current_chart.set_title(title)
        self.current_chart.set_x_label(self.x_label)
        self.current_chart.set_y_label(self.y_label)
        self._render_chart()

    def _value_changed(self, treeview, path, new_value):
        path = int(path)
        self.chart_data[path] = (self.chart_data[path][0], float(new_value))
        self._update_chart_data()

    def _label_changed(self, treeview, path, new_label):
        path = int(path)
        self.chart_data[path] = (new_label, self.chart_data[path][1])
        self._update_chart_data()


class ChartArea(Gtk.DrawingArea):

    def __init__(self, parent):
        """A class for Draw the chart"""
        super(ChartArea, self).__init__()
        self._parent = parent
        self.add_events(Gdk.EventMask.EXPOSURE_MASK |
                        Gdk.EventMask.VISIBILITY_NOTIFY_MASK)
        self.connect("draw", self._draw_cb)

    def _draw_cb(self, widget, context):
        alloc = self.get_allocation()

        # White Background:
        context.rectangle(0, 0, alloc.width, alloc.height)
        context.set_source_rgb(255, 255, 255)
        context.fill()

        # Paint the chart:
        chart_width = self._parent.current_chart.width
        chart_height = self._parent.current_chart.height

        cxpos = alloc.width / 2 - chart_width / 2
        cypos = alloc.height / 2 - chart_height / 2

        context.set_source_surface(self._parent.current_chart.surface,
                                   cxpos,
                                   cypos)
        context.paint()


class ChartData(Gtk.TreeView):

    __gsignals__ = {
             'label-changed': (GObject.SignalFlags.RUN_FIRST, None,
                               [str, str], ),
             'value-changed': (GObject.SignalFlags.RUN_FIRST, None,
                               [str, str], ), }

    def __init__(self, activity):

        GObject.GObject.__init__(self)

        self.model = Gtk.ListStore(str, str)
        self.set_model(self.model)

        self._selection = self.get_selection()
        self._selection.set_mode(Gtk.SelectionMode.SINGLE)

        # Label column
        column = Gtk.TreeViewColumn(_("Label"))
        label = Gtk.CellRendererText()
        label.set_property('editable', True)
        label.connect("edited", self._label_changed, self.model)

        column.pack_start(label, True)
        column.add_attribute(label, 'text', 0)
        self.append_column(column)

        # Value column

        column = Gtk.TreeViewColumn(_("Value"))
        value = Gtk.CellRendererText()
        value.set_property('editable', True)
        value.connect("edited", self._value_changed, self.model, activity)

        column.pack_start(value, True)
        column.add_attribute(value, 'text', 1)

        self.append_column(column)
        self.set_enable_search(False)

        self.show_all()

    def add_value(self, label, value):
        treestore, selected = self._selection.get_selected()
        if not selected:
            path = 0

        elif selected:
            path = int(str(self.model.get_path(selected))) + 1
        try:
            _iter = self.model.insert(path, [label, value])
        except ValueError:
            _iter = self.model.append([label, str(value)])

        self.set_cursor(self.model.get_path(_iter),
                        self.get_column(1),
                        True)

        _logger.info("Added: %s, Value: %s" % (label, value))

        return path

    def _label_changed(self, cell, path, new_text, model):
        _logger.info("Change '%s' to '%s'" % (model[path][0], new_text))
        model[path][0] = new_text

        self.emit("label-changed", str(path), new_text)

    def _value_changed(self, cell, path, new_text, model, activity):
        _logger.info("Change '%s' to '%s'" % (model[path][1], new_text))
        is_number = True
        number = new_text.replace(",", ".")
        try:
            float(number)
        except ValueError:
            is_number = False

        if is_number:
            decimals = utils.get_decimals(str(float(number)))
            new_text = locale.format('%.' + decimals + 'f', float(number))
            model[path][1] = str(new_text)

            self.emit("value-changed", str(path), number)

        elif not is_number:
            _logger.info("Must be a valid value (int)")


class CellRendererActivityIcon(CellRendererIcon):
    __gtype_name__ = 'JournalCellRendererActivityIcon'

    def __init__(self):
        CellRendererIcon.__init__(self)

        self.props.width = style.GRID_CELL_SIZE
        self.props.height = style.GRID_CELL_SIZE
        self.props.size = style.STANDARD_ICON_SIZE
        self.props.mode = Gtk.CellRendererMode.ACTIVATABLE


class HeatMapBlock(Gtk.EventBox):

    __gsignals__ = {
        'on-clicked': (GObject.SignalFlags.RUN_FIRST, None,
                       (int,)),
    }

    def __init__(self, date, contribs, index):
        Gtk.EventBox.__init__(self)

        label = Gtk.Label("   ")
        tooltip = date + "\nContributions:" + str(contribs)
        label.set_tooltip_text(tooltip)

        self.i = index

        if contribs == 0:
            self.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("#cdcfd3"))
        elif contribs <= 2 and contribs > 0:
            self.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("#5fce68"))
        elif contribs <= 5 and contribs > 2:
            self.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("#47a94f"))
        elif contribs >= 6:
            self.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("#38853e"))

        self.add(label)
        self.set_events(Gdk.EventType.BUTTON_PRESS)
        self.connect('button-press-event', self._on_mouse)

    def _on_mouse(self, widget, event):
        self.emit('on-clicked', self.i)
