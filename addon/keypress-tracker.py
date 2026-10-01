# SPDX-License-Identifier: GPL-3.0-or-later

bl_info = {
    "name": "KeyPressTracker",
    "author": "Agoli",  
    "version": (1, 1),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > KeyPressTracker",
    "description": "Compte les touches et raccourcis clavier utilisés dans Blender",
    "category": "3D View",
}

import csv
import time

import bpy
from bpy.app.handlers import persistent
from bpy.props import PointerProperty, StringProperty
from bpy.types import Operator, Panel, PropertyGroup

# -------------------------------------------------------------------
# État global
# -------------------------------------------------------------------
key_counts = {}
last_press_time = {}
is_tracking = False

# CHANGÉ : identifiant de session. Chaque Start crée une nouvelle session ;
# un opérateur modal d'une ancienne session s'arrête tout seul.
# C'est ce qui corrige le bug du double comptage après Stop / Start.
session_id = 0

DEBOUNCE_SECONDS = 0.05

MODIFIER_KEYS = {
    'LEFT_CTRL', 'RIGHT_CTRL', 'LEFT_ALT', 'RIGHT_ALT',
    'LEFT_SHIFT', 'RIGHT_SHIFT', 'OSKEY',
}

MOUSE_EVENTS = {
    'LEFTMOUSE', 'MIDDLEMOUSE', 'RIGHTMOUSE', 'BUTTON4MOUSE',
    'BUTTON5MOUSE', 'BUTTON6MOUSE', 'BUTTON7MOUSE', 'MOUSEMOVE',
    'INBETWEEN_MOUSEMOVE', 'MOUSESMARTZOOM', 'WHEELUPMOUSE',
    'WHEELDOWNMOUSE', 'WHEELINMOUSE', 'WHEELOUTMOUSE',
    'TRACKPADPAN', 'TRACKPADZOOM', 'MOUSEROTATE', 'PEN', 'ERASER',
}

# CHANGÉ : événements internes de Blender qui ne sont pas des touches.
IGNORED_PREFIXES = ('TIMER', 'NDOF', 'WINDOW', 'ACTIONZONE', 'XR', 'EVT_')
IGNORED_EVENTS = {'NONE', 'TEXTINPUT'}


def is_keyboard_event(event_type):
    if event_type in MOUSE_EVENTS or event_type in IGNORED_EVENTS:
        return False
    return not event_type.startswith(IGNORED_PREFIXES)


def active_modifiers(event, exclude=None):
    """Liste des modificateurs actifs, sauf celui qu'on est en train d'appuyer."""
    mods = []
    if event.ctrl and exclude != "Ctrl":
        mods.append("Ctrl")
    if event.shift and exclude != "Shift":
        mods.append("Shift")
    if event.alt and exclude != "Alt":
        mods.append("Alt")
    # CHANGÉ : la touche Windows / Cmd est maintenant prise en compte.
    if event.oskey and exclude != "OS":
        mods.append("OS")
    return mods


def modifier_name(event_type):
    if 'CTRL' in event_type:
        return "Ctrl"
    if 'SHIFT' in event_type:
        return "Shift"
    if 'ALT' in event_type:
        return "Alt"
    return "OS"


def redraw_3d_views(context):
    wm = context.window_manager if context else bpy.context.window_manager
    for window in wm.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()


# -------------------------------------------------------------------
# Opérateur modal qui écoute le clavier
# -------------------------------------------------------------------
class KPT_OT_Tracker(Operator):
    """Écoute les événements clavier"""
    bl_idname = "wm.kpt_tracker"
    bl_label = "Key Press Tracker"

    # CHANGÉ : plus de timer à 0,001 s. Il réveillait Blender mille fois
    # par seconde pour rien : les événements clavier arrivent tout seuls.

    def invoke(self, context, event):
        self.my_session = session_id
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        # CHANGÉ : si le suivi est arrêté, ou si une nouvelle session a été
        # lancée, cet opérateur se termine au lieu de rester en vie.
        if not is_tracking or self.my_session != session_id:
            return {'CANCELLED'}

        # CHANGÉ : on ignore les répétitions d'une touche maintenue.
        if event.value != 'PRESS' or event.is_repeat:
            return {'PASS_THROUGH'}

        if not is_keyboard_event(event.type):
            return {'PASS_THROUGH'}

        if event.type in MODIFIER_KEYS:
            # CHANGÉ : on retire le modificateur qu'on appuie de la liste,
            # pour que "Ctrl seul" soit bien compté même si Blender
            # considère déjà Ctrl comme actif à cet instant.
            if active_modifiers(event, exclude=modifier_name(event.type)):
                return {'PASS_THROUGH'}
            combo = event.type
        else:
            combo = "+".join(active_modifiers(event) + [event.type])

        now = time.time()
        if now - last_press_time.get(combo, 0.0) > DEBOUNCE_SECONDS:
            key_counts[combo] = key_counts.get(combo, 0) + 1
            last_press_time[combo] = now
            redraw_3d_views(context)

        return {'PASS_THROUGH'}


# -------------------------------------------------------------------
# Sauvegarde
# -------------------------------------------------------------------
def save_counts(path):
    """CHANGÉ : export en CSV, ouvrable dans un tableur."""
    sorted_keys = sorted(key_counts.items(), key=lambda x: -x[1])
    with open(bpy.path.abspath(path), "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["touche", "nombre"])
        writer.writerows(sorted_keys)


# -------------------------------------------------------------------
# Propriétés et panneau
# -------------------------------------------------------------------
class KPTProperties(PropertyGroup):
    file_path: StringProperty(
        name="Fichier",
        description="Fichier CSV où enregistrer les résultats",
        default="//key_counts.csv",
        subtype='FILE_PATH',
    )


class KPT_PT_MainPanel(Panel):
    bl_label = "KeyPressTracker"
    bl_idname = "KPT_PT_mainpanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "KeyPressTracker"

    def draw(self, context):
        layout = self.layout
        props = context.scene.kpt_props

        layout.prop(props, "file_path", text="Fichier")

        row = layout.row()
        if is_tracking:
            row.operator("kpt.stop_tracking", text="Stop", icon='PAUSE')
        else:
            row.operator("kpt.start_tracking", text="Start", icon='PLAY')

        box = layout.box()
        status = box.row()
        status.scale_y = 1.3
        status.alignment = 'CENTER'
        if is_tracking:
            status.label(text="● En cours", icon='CHECKMARK')
        else:
            box.alert = True
            status.label(text="● Arrêté", icon='CANCEL')

        row = layout.row(align=True)
        row.operator("kpt.save", text="Enregistrer", icon='FILE_TICK')
        row.operator("kpt.reset", text="Remettre à zéro", icon='TRASH')

        layout.separator()
        total = sum(key_counts.values())
        layout.label(text=f"Top 10 ({total} appuis au total) :")

        col = layout.column(align=True)
        sorted_keys = sorted(key_counts.items(), key=lambda x: -x[1])[:10]
        if not sorted_keys:
            col.label(text="Aucune touche enregistrée.")
        for key, count in sorted_keys:
            col.label(text=f"{key} : {count}")


# -------------------------------------------------------------------
# Opérateurs Start / Stop / Enregistrer / Reset
# -------------------------------------------------------------------
class KPT_OT_Start(Operator):
    bl_idname = "kpt.start_tracking"
    bl_label = "Start"
    bl_description = "Commencer à compter les touches"

    def execute(self, context):
        global is_tracking, session_id
        if is_tracking:
            self.report({'INFO'}, "Déjà en cours.")
            return {'CANCELLED'}

        session_id += 1
        is_tracking = True
        bpy.ops.wm.kpt_tracker('INVOKE_DEFAULT')
        self.report({'INFO'}, "Comptage démarré.")
        return {'FINISHED'}


class KPT_OT_Stop(Operator):
    bl_idname = "kpt.stop_tracking"
    bl_label = "Stop"
    bl_description = "Arrêter le comptage et enregistrer les résultats"

    def execute(self, context):
        global is_tracking
        if not is_tracking:
            self.report({'INFO'}, "Pas en cours.")
            return {'CANCELLED'}

        is_tracking = False
        bpy.ops.kpt.save()
        redraw_3d_views(context)
        return {'FINISHED'}


class KPT_OT_Save(Operator):
    bl_idname = "kpt.save"
    bl_label = "Enregistrer"
    bl_description = "Enregistrer les résultats dans le fichier CSV"

    def execute(self, context):
        path = context.scene.kpt_props.file_path
        if not path:
            self.report({'WARNING'}, "Aucun fichier choisi, rien n'a été enregistré.")
            return {'CANCELLED'}
        try:
            save_counts(path)
        except OSError as e:
            self.report({'ERROR'}, f"Échec de l'enregistrement : {e}")
            return {'CANCELLED'}
        self.report({'INFO'}, f"Enregistré dans {path}")
        return {'FINISHED'}


class KPT_OT_Reset(Operator):
    """CHANGÉ : nouveau bouton pour repartir de zéro"""
    bl_idname = "kpt.reset"
    bl_label = "Remettre à zéro"
    bl_description = "Effacer tous les comptages"

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        key_counts.clear()
        last_press_time.clear()
        redraw_3d_views(context)
        return {'FINISHED'}


# -------------------------------------------------------------------
# Ouverture d'un autre fichier
# -------------------------------------------------------------------
@persistent
def on_load_pre(*args):
    """CHANGÉ : ouvrir un autre .blend arrête l'opérateur modal.
    On remet l'état à "Arrêté" pour que l'interface ne mente pas."""
    global is_tracking
    is_tracking = False


# -------------------------------------------------------------------
# Enregistrement
# -------------------------------------------------------------------
classes = (
    KPTProperties,
    KPT_OT_Tracker,
    KPT_PT_MainPanel,
    KPT_OT_Start,
    KPT_OT_Stop,
    KPT_OT_Save,
    KPT_OT_Reset,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.kpt_props = PointerProperty(type=KPTProperties)
    bpy.app.handlers.load_pre.append(on_load_pre)


def unregister():
    global is_tracking
    is_tracking = False
    if on_load_pre in bpy.app.handlers.load_pre:
        bpy.app.handlers.load_pre.remove(on_load_pre)
    del bpy.types.Scene.kpt_props
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()