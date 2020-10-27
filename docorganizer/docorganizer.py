#!/usr/bin/env python3
# V. 1.0
############# PERSONALIZATION #############
# size of the main window
WWIDTH=1100
WHEIGHT=800

ICON_SIZE = 128
LINK_SIZE = 48
THUMB_SIZE = 128
# -1 to use the default value
IV_ITEM_WIDTH = 140
# use the thumbnails if it exists - 0 No - 1 the existent ones - 2 use the custom thumbnailers (not implemented)
USE_THUMB = 1

################### END ###################

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Gio, GObject, Pango
from gi.repository.GdkPixbuf import Pixbuf
import datetime, os, sys, time
import hashlib
import subprocess, shutil


# the program
class MainWindow(Gtk.Window):

    def __init__(self):
        Gtk.Window.__init__(self)
        self.set_default_size(WWIDTH, WHEIGHT)
        header = Gtk.HeaderBar(title="Docorganizer")
        header.props.show_close_button = False
        
        ## close this program
        close_button = Gtk.Button(label=None, image=Gtk.Image.new_from_icon_name("exit", Gtk.IconSize.BUTTON))
        close_button.set_tooltip_text("Exit")
        self.connect("delete-event", self.on_exit)
        close_button.connect("clicked", self.on_exit2)
        header.pack_end(close_button)
        
        self.set_titlebar(header)
        
        #### the main box
        self.mbox = Gtk.Box(orientation=0, spacing=0)
        
        self.add(self.mbox)
        
        self.show_all()
        #
        wiconview(None, self)
    
    
    # main window
    def on_exit(self, w, e):
        self.on_exit2(w)
        return True
    
    # button quit
    def on_exit2(self, w):
        Gtk.main_quit()


############### ICONVIEW

class CellRenderer(Gtk.CellRendererPixbuf):
    
    def __init__(self):
        super().__init__()
        self.set_fixed_size(THUMB_SIZE+2, THUMB_SIZE+2)
        
    def do_render(self, cr, widget, background_area, cell_area, flags):
        
        x_offset = cell_area.x 
        y_offset = cell_area.y
        
        PPIXBUF = self.props.pixbuf
        
        xadd = 0
        if PPIXBUF.get_width() < cell_area.width:
            xadd = (cell_area.width - PPIXBUF.get_width())/2
        yadd = 0
        if PPIXBUF.get_height() < cell_area.height:
            yadd = (cell_area.height - PPIXBUF.get_height())
        pixbufimage = PPIXBUF
        Gdk.cairo_set_source_pixbuf(cr, pixbufimage, x_offset+xadd, y_offset+yadd)
        #
        cr.paint()
        
        xpad = cell_area.width-10
        ypad = THUMB_SIZE-LINK_SIZE
        
        
class CellArea(Gtk.CellAreaBox):
    
    def __init__(self):
        super().__init__()
        
        renderer_thumb = CellRenderer()
        self.pack_start(renderer_thumb, False, False, 0)
        self.attribute_connect(renderer_thumb, "pixbuf", 0)
        
        renderer1 = Gtk.CellRendererText()
        self.pack_start(renderer1, False, False, 0)
        renderer1.props.xalign = 0.5
        renderer1.props.yalign = 0
        renderer1.props.wrap_width = 15
        renderer1.props.wrap_mode = 1
        renderer1.props.style = 1
        self.add_attribute(renderer1, 'text', 4)
        
        renderer = Gtk.CellRendererText()
        self.pack_end(renderer, True, True, 0)
        renderer.props.xalign = 0.5
        renderer.props.yalign = 0
        renderer.props.wrap_width = 15
        renderer.props.wrap_mode = 1
        self.add_attribute(renderer, 'text', 1)
        

class wiconview():
    def __init__(self, working_dir, window):
        self.window = window
        #
        self.working_path = "collections/default"
        #
        # main box
        self.IVBox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        # scrolled window
        scrolledwindow = Gtk.ScrolledWindow()
        self.IVBox.add(scrolledwindow)
        scrolledwindow.set_overlay_scrolling(True)
        scrolledwindow.set_hexpand(True)
        scrolledwindow.set_vexpand(True)
        scrolledwindow.set_policy(Gtk.PolicyType.NEVER,  Gtk.PolicyType.AUTOMATIC)
        ################
        # item icon - item name - folder container name - real file full path - date - comment
        self.model = Gtk.ListStore(Pixbuf, str, str, str, str, str)
        self.fill_model()
        #
        self.model.set_sort_column_id(4, Gtk.SortType.ASCENDING)
        #
        self.IV = Gtk.IconView.new_with_area(CellArea())
        scrolledwindow.add(self.IV)
        #
        self.IV.set_model(self.model)
        #
        if IV_ITEM_WIDTH != -1:
            self.IV.set_item_width(IV_ITEM_WIDTH)
        #
        self.IV.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.IV.set_tooltip_column(5)
        # the selected item
        self.selected_target = None
        #
        self.window.mbox.pack_start(self.IVBox, True, True, 0)
        ## DnD
        gte = Gtk.TargetEntry.new("text/uri-list", Gtk.TargetFlags.OTHER_APP, 0)
        targets = [gte]
        # drag
        start_button_mask = Gdk.ModifierType.BUTTON1_MASK
        actions = Gdk.DragAction.COPY
        self.IV.enable_model_drag_source(start_button_mask, targets, actions)
        self.IV.connect_after("drag-begin", self.on_drag_begin)
        self.IV.connect("drag-data-get", self.on_drag_data_get)
        self.IV.connect("drag-end", self.on_drag_end)
        self.IV.connect("drag-failed", self.on_drag_failed)
        self.IV.connect("drag-motion", self.on_drag_motion)
        # drop
        actions_drop = Gdk.DragAction.COPY
        self.IV.enable_model_drag_dest(targets, actions_drop)
        self.IV.connect("drag-drop", self.on_drag_drop)
        self.IV.connect("drag-data-received", self.on_drop_data_received)
        ## mouse events
        self.IV.connect("item-activated", self.on_double_click)
        self.IV.connect("button-press-event", self.on_mouse_button_pressed)
        self.IV.connect("button-release-event", self.on_mouse_release)
    
    
    # delete the selected item
    def delete_item(self, w):
        dialog = DialogYN(self.window, "  Delete?  ", "\n Do you want to delete the selected document? \n")
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            # the folder to delete
            ifoldername = self.model[self.selected_target][2]
            ifolder = os.path.join(self.working_path, ifoldername)
            try:
                # remove the selected item
                iiter = self.model.get_iter(self.selected_target)
                self.model.remove(iiter)
                shutil.rmtree(ifolder, ignore_errors=True)
                self.selected_target = None
            except Exception as E:
                self.generic_dialog("Error", "\n{}\n".format(str(E)))
            dialog.destroy()
        dialog.destroy()
    
    # modify the selected item data
    def modify_item(self, w):
        #
        rrow = self.selected_target
        idate = self.model[rrow][4]
        icomment = self.model[rrow][5]
        #
        dialog = modifyClass(self.window, "Modify", [idate, icomment])
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            result = dialog.get_result()
            dialog.destroy()
        else:
            dialog.destroy()
            return
        # 
        if result:
            newdate = result[0]
            newcomment = result[1].strip()
            # modify the item in the model
            try:
                iiter = self.model.get_iter(self.selected_target)
                ## the dir and files
                itemfolder = self.model[self.selected_target][2]
                ddir = os.path.join(self.working_path, itemfolder)
                #
                fdate = os.path.join(ddir, "date")
                fcomment = os.path.join(ddir, "comment")
                #
                with open(fdate, "w") as f:
                    f.write(newdate)
                if newcomment == "":
                    newcomment = "No comment"
                self.model.set_value(iiter, 5, newcomment)
                with open(fcomment, "w") as f:
                    f.write(newcomment)
                # must be the last
                self.model.set_value(iiter, 4, newdate)
            except Exception as E:
                self.generic_dialog("", "\n{}\n".format(str(E)))
    
    # the data of the selected item
    def property_item(self, w):
        pfile = self.model[self.selected_target][3]
        real_path = os.path.realpath(pfile)
        if os.path.islink(pfile):
            real_path = "Link to: " + real_path
        self.generic_dialog("", "{}\n\n{}".format(real_path, self.model[self.selected_target][5]))
    
    # open the folder that contains the selected file with the default program
    def open_item(self, w):
        fpath = self.model[self.selected_target][3]
        f = Gio.File.new_for_path(os.path.dirname(fpath))
        uri = f.get_uri()
        try:
            ret = Gio.app_info_launch_default_for_uri(uri, None)
            if ret == False:
                self.generic_dialog("Error", os.path.basename(os.path.dirname(fpath)))
        except Exception as E:
            self.generic_dialog("Error", str(E))
    
    # open the file with the default program
    def on_double_click(self, IV, treepath):
        fpath = self.model[treepath][3]
        f = Gio.File.new_for_path(fpath)
        uri = f.get_uri()
        try:
            ret = Gio.app_info_launch_default_for_uri(uri, None)
            if ret == False:
                self.generic_dialog("Error", os.path.basename(fpath))
        except Exception as e:
            self.generic_dialog("Error", os.path.basename(fpath))

    # menu on selected item - RMB
    def on_mouse_button_pressed(self, IV, event):
        if event.button == 3:
            target = IV.get_path_at_pos(int(event.x), int(event.y))
            if target:
                if not os.path.exists(self.model[target][3]):
                    self.selected_target = target
                    IV.select_path(target)
                    mpop = Gtk.Menu()
                    self.populate_menu_missed(mpop) 
                    return
                self.selected_target = target
                IV.select_path(target)
                mpop = Gtk.Menu()
                self.populate_menu(mpop) 
    
    # the menu for missed file
    def populate_menu_missed(self, mpop):
        # the treepath
        rrow = self.IV.get_selected_items()[0]
        # delete
        item10 = Gtk.MenuItem(label="Delete")
        mpop.append(item10)
        item10.connect("activate", self.delete_item)
        
        # separator
        mpop.append(Gtk.SeparatorMenuItem())
        
        # file path
        item21 = Gtk.MenuItem(label="File property")
        mpop.append(item21)
        item21.connect("activate", self.property_item)
        
        mpop.popup(None, None, None, None, 0, Gtk.get_current_event_time())
        mpop.show_all()
    
    # the menu
    def populate_menu(self, mpop):
        # the treepath
        rrow = self.IV.get_selected_items()[0]
        item0000 = Gtk.MenuItem(label="Open with..")
        mpop.append(item0000)
        
        # other applications submenu
        mpopaa = Gtk.Menu()
        fpath = self.model[rrow][3]
        # find the mimetype
        ffile = Gio.File.new_for_path(fpath)
        try:
            file_info = ffile.query_info('standard::content-type', Gio.FileQueryInfoFlags.NONE, None)
        except Exception as e:
            self.generic_dialog("\n"+str(e), "")
            return
        fmime = Gio.FileInfo.get_content_type(file_info)
        #
        dialog = Gtk.AppChooserDialog.new_for_content_type(self.window, 0, fmime)
        #
        item0000.props.submenu = mpopaa
        appinfo = dialog.get_app_info()
        if appinfo:
            alist = appinfo.get_recommended_for_type(fmime)
            for el in alist:
                item = Gtk.MenuItem(label=el.get_display_name())
                mpopaa.append(item)
                item.connect("activate", self.on_open_aa, el.get_executable(), fpath)
            # separator
            mpopaa.append(Gtk.SeparatorMenuItem())
        
        # 
        itemaa = Gtk.MenuItem(label="Other applications")
        itemaa.connect("activate", self.on_other_applications, fpath)
        mpopaa.append(itemaa)
        
        # separator
        mpop.append(Gtk.SeparatorMenuItem())
        
        # delete
        item10 = Gtk.MenuItem(label="Delete")
        mpop.append(item10)
        item10.connect("activate", self.delete_item)
        
        # modify
        item11 = Gtk.MenuItem(label="Modify")
        mpop.append(item11)
        item11.connect("activate", self.modify_item)
        
        # separator
        mpop.append(Gtk.SeparatorMenuItem())
        
        # open the folder
        # file path
        item20 = Gtk.MenuItem(label="Open the folder")
        mpop.append(item20)
        item20.connect("activate", self.open_item)
        
        # file path
        item21 = Gtk.MenuItem(label="File property")
        mpop.append(item21)
        item21.connect("activate", self.property_item)
        
        mpop.popup(None, None, None, None, 0, Gtk.get_current_event_time())
        mpop.show_all()

    # open the file with the program choosen
    def on_open_aa(self, widget, executable, fpath):
        if shutil.which(executable):
            try:
                subprocess.Popen([executable, fpath])
            except Exception as e:
                self.generic_dialog("\n"+str(e), "")

    # open with other applications
    def on_other_applications(self, widget, fpath):
        ffile = Gio.File.new_for_path(fpath)
        file_info = ffile.query_info('standard::content-type', Gio.FileQueryInfoFlags.NONE, None)
        fmime = Gio.FileInfo.get_content_type(file_info)
        #
        dialog = Gtk.AppChooserDialog.new_for_content_type(self.window, 0, fmime)
        if (dialog.run () == Gtk.ResponseType.OK):
            appinfo = dialog.get_app_info()
            alist = appinfo.get_recommended_for_type(fmime)
            if appinfo:
                # open the file
                gpath = Gio.File.new_for_path(fpath)
                appinfo.launch((gpath,), None)
            
            dialog.destroy()
        else:
            dialog.destroy()

###### DnD
    
    ### DRAG

    def on_drag_data_get(self, IV, context, selection, info, time):
        
        if IV.get_selected_items() != None:
            rrow = IV.get_selected_items()[0]
            fpath = self.model[rrow][3]
            f = Gio.File.new_for_path(fpath)
            uri = f.get_uri()
            selection.set(selection.get_target(), 8, uri.encode())
        
    def on_drag_begin(self, IV, context):
        if len(IV.get_selected_items()) == 1:
            row = IV.get_selected_items()[0]
            pixbuf = self.model[row][0]
            Gtk.drag_set_icon_pixbuf(context, pixbuf, 10, 10)

    def on_drag_end(self, IV, context):
        return True

    def on_drag_failed(self, IV, context, result):
        pass

    def on_drag_data_delete(self, IV, context):
        pass
    
    def on_drag_motion(self, IV, context, x, y, time):
        return False

    ### drop

    # 
    def on_drag_drop(self, IV, context, x, y, time):
        IV.stop_emission_by_name('drag-drop')
        IV.drag_get_data(context, Gdk.Atom.intern('text/uri-list', False), time)
        return True
    
    # drop
    def on_drop_data_received(self, IV, context, x, y, selection, info, time):
        
        IV.stop_emission_by_name('drag-data-received')
        
        DATA = selection.get_uris()
        
        if len(DATA) > 0:
            for ddata in DATA:
                f = Gio.file_new_for_uri(ddata)
                ffile = f.get_path()
                if os.path.isfile(ffile):
                    # today - date and time
                    z = datetime.datetime.now()
                    #dY, dM, dD, dH, dm, ds, dms
                    itemdate = "{}.{}.{}_{}.{}.{}".format(z.year, z.month, z.day, z.hour, z.minute, z.second)
                    #
                    try:
                        ## the dir
                        ddir = os.path.join(self.working_path, itemdate)
                        ## make the dir
                        os.mkdir(ddir)
                        ## create the files
                        dfile = os.path.join(ddir, "item")
                        f = open(dfile,"w")
                        f.write(ffile)
                        f.close()
                        # the date file
                        fdate = "{}{}{}".format(z.year, z.month, z.day)
                        f = open(os.path.join(ddir, "date"), "w")
                        f.write(fdate)
                        f.close()
                        # the comments file
                        dfilec = os.path.join(ddir, "comment")
                        f = open(dfilec,"w")
                        f.write("No comment")
                        f.close()
                        # fill the model
                        self.storeItem(ffile, itemdate, fdate, "No comment")
                    except Exception as E:
                        self.generic_dialog("\n"+str(E), "")
            self.IV.grab_focus()
            context.finish(True, False, time)
        else:
            context.finish(False, False, time)

#########

    # LMB - release
    def on_mouse_release(self, IV, event):
        tpath = IV.get_path_at_pos(int(event.x), int(event.y))
        if not tpath:
            # reset clicking in the background
            self.selected_target = None

    # the list of the items in the folder
    def get_items(self, npath, ffolder):
        list_items = []
        path = os.path.join(npath, ffolder)
        ffile = os.path.join(path, "item")
        try:
            f = open(ffile, "r")
            file_path = f.readline().strip()
            f.close()
            list_items.append(file_path)
        except:
            pass
            
        return list_items
    
    # fill the model
    def fill_model(self):
        npath = self.working_path
        try:
            folder_folders = os.listdir(npath)
        except Exception as E:
            folder_folders = []
            self.generic_dialog("\n"+str(E), "")
            sys.exit()
        #
        for ffolder in folder_folders:
            list_items = []
            list_items = self.get_items(npath, ffolder)
            #
            for file_path in list_items:
                if file_path:
                    fdate = ""
                    with open(os.path.join("collections/default", ffolder, "date"), "r") as f:
                        fdate = f.readline().strip()
                    with open(os.path.join("collections/default", ffolder, "comment"), "r") as f:
                        fcomm = f.readline().strip()
                    #
                    if not fcomm:
                        fcomm = "No comment"
                    #
                    self.storeItem(file_path, ffolder, fdate, fcomm)
        
    # service function
    def storeItem(self, file_path, ffolder, fdate, fcomm):
        pixbuf = self.evaluate_pixbuf(file_path, ICON_SIZE)
        iitem = os.path.basename(file_path)
        #
        if not os.path.exists(file_path):
            iitem += "\n(file missed)"
        # icon - name - folder container name - real file full path - date - comment
        self.model.append([pixbuf, iitem, ffolder, file_path, fdate, fcomm])
    
    # get the default icon for the item
    def evaluate_pixbuf(self, path, iicon_size):
        f = Gio.file_new_for_path(path)
        #
        try:
            info = f.query_info(Gio.FILE_ATTRIBUTE_STANDARD_ICON,
                        Gio.FileQueryInfoFlags.NONE, None)
        except:
            pixbuf = Gtk.IconTheme.get_default().load_icon("empty", ICON_SIZE, 0)   
            return pixbuf
        
        gicon = info.get_icon()
        gicon.get_names()
        
        #
        if USE_THUMB == 1:
            thumbpath = self.fthumbnailfile(f.get_uri())
            if thumbpath is not None:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(thumbpath, THUMB_SIZE, THUMB_SIZE)
                return pixbuf
        elif USE_THUMB == 2:
            # CUSTOM THUMBNAILERS - not implemented
            pass
        #
        try:
            pixbuf = Gtk.IconTheme.get_default().load_icon(gicon.get_names()[0], iicon_size, 0)
            return pixbuf
        except:
            try:
                pixbuf = Gtk.IconTheme.get_default().load_icon(gicon.get_names()[1], iicon_size, 0)
                return pixbuf
            except:
                pixbuf = Gtk.IconTheme.get_default().load_icon("empty", ICON_SIZE, 0)   
                return pixbuf

    # get the thumbnail for the file if it exists
    def fthumbnailfile(self, furi):
        hmd5 = hashlib.md5(bytes(furi, "utf-8")).hexdigest()
        # the thumbnail file is stored in the ~/.thumbnails/normal folder
        thumbfilename = os.path.join(os.path.expanduser('~/.cache/thumbnails/normal'), hmd5) + '.png'
        #
        if os.path.exists(thumbfilename):
            return thumbfilename
        else:
            return None
    
    # generic dialog
    def generic_dialog(self, message1, message2):
        dialog = Gtk.MessageDialog(parent=self.window, flags=0, message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK, text=message1)
        dialog.format_secondary_text("{}".format(message2))
        dialog.run()
        dialog.destroy()

# dialog : modify an item
class modifyClass(Gtk.Dialog):
    def __init__(self, parent, title, data):
        Gtk.Dialog.__init__(self, title=title, transient_for=parent, flags=0)
        self.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK
        )

        self.set_default_size(500, 100)
        
        # the data to modify
        self.data = data
        
        # the returning value
        self.value = None
        
        #
        self.connect("response", self.on_response)

        box = self.get_content_area()
        
        #
        cframe = Gtk.Frame(label="  Comment  ")
        box.add(cframe)
        self.description = Gtk.TextView()
        buffer = self.description.get_buffer()
        buffer.set_text(self.data[1])
        cframe.add(self.description)
        
        ## date
        sframe = Gtk.Frame(label="  Date  ")
        box.add(sframe)
        # calendar
        self.scalendar = Gtk.Calendar()
        # date
        year = self.data[0][0:4]
        month = self.data[0][4:6]
        day = self.data[0][6:8]
        self.scalendar.select_month(int(month)-1, int(year))
        self.scalendar.select_day(int(day))
        #
        sframe.add(self.scalendar)
        
        ##
        self.show_all()
    
    def on_response(self, widget, response_id):
        self.value = []
        # calendar
        lstext = "{}{:02d}{:02d}".format(self.scalendar.get_date().year, self.scalendar.get_date().month+1, self.scalendar.get_date().day)
        self.value.append(lstext)
        # comments
        buffer = self.description.get_buffer()
        startIter, endIter = buffer.get_bounds()    
        text = buffer.get_text(startIter, endIter, False)
        self.value.append(text)
    
    def get_result(self):
        return self.value


# dialog
class DialogYN(Gtk.Dialog):
    def __init__(self, parent, title, info):
        Gtk.Dialog.__init__(self, title=title, transient_for=parent, flags=0)
        self.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK
        )

        self.set_default_size(150, 100)

        label = Gtk.Label(label=info)

        box = self.get_content_area()
        box.add(label)
        self.show_all()
    

if __name__ == "__main__":
    win = MainWindow()
    win.show_all()
    Gtk.main()
