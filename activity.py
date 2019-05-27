# Copyright 2009 Simon Schampijer
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

"""HelloWorld Activity: A case study for developing an activity."""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, Pango

from gettext import gettext as _

from sugar3.activity import activity
from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.activity.widgets import ActivityButton
from sugar3.activity.widgets import StopButton
from sugar3.datastore import datastore

from jarabe.model import bundleregistry
from collections import Counter

class DashboardActivity(activity.Activity):

    def __init__(self, handle):

        activity.Activity.__init__(self, handle)

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

        # Grid as the main container
        grid = Gtk.Grid(column_spacing=5.5, row_spacing=3)
      
        self.add(grid)
        self.set_canvas(grid)

        vbox_total_activities = Gtk.VBox()
        vbox_journal_entries = Gtk.VBox()
        vbox_total_contribs = Gtk.VBox()

        # VBoxes for total activities, journal entries and ??
        vbox_total_activities.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        vbox_journal_entries.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        vbox_total_contribs.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))

        label_dashboard = Gtk.Label()
        label_dashboard.set_markup(_("<b>Dashboard</b>"))

        # label for total activities
        label_TA = Gtk.Label()
        label_TA.set_markup(_("<b>Activities Installed</b>"))
        vbox_total_activities.add(label_TA)

        label_total_activities = Gtk.Label()
        vbox_total_activities.add(label_total_activities)

        # label for total journal entries
        label_JE = Gtk.Label()
        label_JE.set_markup(_("<b>Journal Entries</b>"))
        vbox_journal_entries.add(label_JE)

        label_journal_entries = Gtk.Label()
        vbox_journal_entries.add(label_journal_entries)

        # label for ??
        label_CE = Gtk.Label()
        label_CE.set_markup(_("<b>Total Files</b>"))
        vbox_total_contribs.add(label_CE)
    
        label_contribs = Gtk.Label()
        vbox_total_contribs.add(label_contribs)

        # empty label

        label_empt = Gtk.Label("")

        # font
        font_main = Pango.FontDescription("Dejavu Sans Mono 14")
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
        
        files_list = []
        mime_types = ['image/bmp', 'image/gif', 'image/jpeg',
                        'image/png', 'image/tiff', 'application/pdf',
                        'text/plain']
        label_test = Gtk.Label()

        for dsobject in dsobjects:
            if dsobject.metadata['mime_type'] in mime_types:
                files_list.append(dsobject.metadata['title'])
                #files_list.append('\n')

        label_total_activities.set_text(str(len(registry)))
        label_journal_entries.set_text(str(journal_entries))
        label_contribs.set_text(str(len(files_list)))

        grid.attach(label_dashboard, 2, 2, 20, 20)
        grid.attach_next_to(label_empt, label_dashboard, Gtk.PositionType.BOTTOM, 6, 1)
        grid.attach_next_to(vbox_total_activities, label_empt, Gtk.PositionType.RIGHT, 50, 50)
        grid.attach_next_to(vbox_journal_entries, vbox_total_activities, Gtk.PositionType.RIGHT, 50, 50)
        grid.attach_next_to(vbox_total_contribs, vbox_journal_entries, Gtk.PositionType.RIGHT, 50, 50)
        grid.show_all()
    