"""
Casa medieval enxaimel (somente a parte externa)
Blender 3.6+ / 4.x / 5.x  ->  aba Scripting > New > colar > Run Script (Alt+P)

Escala em metros (casa ~ 6 x 5,3 m, ~10 m de altura com a chaminé).
Frente da casa = lado -Y (a câmera já está posicionada para ele).
"""
import bpy
import math
import random
from mathutils import Vector

random.seed(7)

# ----------------------------------------------------------------- limpeza
if bpy.context.object and bpy.context.object.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.lights,
             bpy.data.cameras, bpy.data.curves):
    for b in list(coll):
        coll.remove(b)

# ----------------------------------------------------------------- medidas
XW = 2.9            # meia largura das paredes
Z_B = 0.9           # topo da base de pedra
Z_F = 3.5           # piso do andar de cima (nível do balanço)
Z_E = 5.9           # beiral
Y_FRONT_G = -2.4    # parede da frente (térreo)
Y_FRONT_U = -2.9    # parede da frente (andar de cima, em balanço)
Y_BACK = 2.4
Y0 = (Y_FRONT_U + Y_BACK) / 2      # centro do andar de cima em Y
HS = (Y_BACK - Y_FRONT_U) / 2      # meio vão do telhado
PITCH = math.radians(45)
HR = HS * math.tan(PITCH)          # altura do telhado


# ================================================================= MATERIAIS
def new_mat(name):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return m, nt, bsdf


def ramp(nt, stops):
    r = nt.nodes.new("ShaderNodeValToRGB")
    cr = r.color_ramp
    while len(cr.elements) < len(stops):
        cr.elements.new(1.0)
    for e, (p, c) in zip(cr.elements, stops):
        e.position = p
        e.color = (c[0], c[1], c[2], 1.0)
    return r


def obj_coord(nt):
    return nt.nodes.new("ShaderNodeTexCoord").outputs["Object"]


def noise(nt, scale, detail=6, rough=0.55):
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = rough
    return n


def bump(nt, strength, dist=0.01):
    b = nt.nodes.new("ShaderNodeBump")
    b.inputs["Strength"].default_value = strength
    b.inputs["Distance"].default_value = dist
    return b


def mat_stone(name="Pedra", scale=4.5):
    m, nt, b = new_mat(name)
    L = nt.links.new
    tc = obj_coord(nt)
    v1 = nt.nodes.new("ShaderNodeTexVoronoi")
    v1.feature = 'F1'
    v2 = nt.nodes.new("ShaderNodeTexVoronoi")
    v2.feature = 'DISTANCE_TO_EDGE'
    for v in (v1, v2):
        v.inputs["Scale"].default_value = scale
        v.inputs["Randomness"].default_value = 0.9
        L(tc, v.inputs["Vector"])
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    L(v1.outputs["Color"], sep.inputs["Color"])
    shade = nt.nodes.new("ShaderNodeMath")
    shade.operation = 'MULTIPLY_ADD'
    shade.inputs[1].default_value = 0.5
    shade.inputs[2].default_value = 0.45
    L(sep.outputs["Red"], shade.inputs[0])
    edge = ramp(nt, [(0.0, (0, 0, 0)), (0.09, (1, 1, 1))])
    L(v2.outputs["Distance"], edge.inputs["Fac"])
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = 'MULTIPLY'
    L(shade.outputs["Value"], mul.inputs[0])
    L(edge.outputs["Color"], mul.inputs[1])
    col = ramp(nt, [(0.0, (0.02, 0.02, 0.02)), (1.0, (0.50, 0.46, 0.40))])
    L(mul.outputs["Value"], col.inputs["Fac"])
    L(col.outputs["Color"], b.inputs["Base Color"])
    bm = bump(nt, 0.9, 0.03)
    L(edge.outputs["Color"], bm.inputs["Height"])
    L(bm.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Roughness"].default_value = 0.92
    return m


def mat_plaster():
    m, nt, b = new_mat("Reboco")
    L = nt.links.new
    tc = obj_coord(nt)
    n1 = noise(nt, 2.5, 10, 0.6)
    L(tc, n1.inputs["Vector"])
    col = ramp(nt, [(0.3, (0.50, 0.43, 0.31)), (0.7, (0.78, 0.72, 0.58))])
    L(n1.outputs["Fac"], col.inputs["Fac"])
    L(col.outputs["Color"], b.inputs["Base Color"])
    n2 = noise(nt, 70, 4, 0.6)
    L(tc, n2.inputs["Vector"])
    bm = bump(nt, 0.5, 0.01)
    L(n2.outputs["Fac"], bm.inputs["Height"])
    L(bm.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Roughness"].default_value = 0.95
    return m


def mat_wood_beam():
    m, nt, b = new_mat("Madeira_Viga")
    L = nt.links.new
    tc = obj_coord(nt)
    w = nt.nodes.new("ShaderNodeTexWave")
    w.wave_type = 'BANDS'
    w.bands_direction = 'Z'      # veios ao longo da viga
    w.inputs["Scale"].default_value = 6
    w.inputs["Distortion"].default_value = 6
    w.inputs["Detail"].default_value = 2
    L(tc, w.inputs["Vector"])
    col = ramp(nt, [(0.0, (0.035, 0.02, 0.012)), (1.0, (0.15, 0.09, 0.05))])
    L(w.outputs["Fac"], col.inputs["Fac"])
    L(col.outputs["Color"], b.inputs["Base Color"])
    n = noise(nt, 40, 5)
    L(tc, n.inputs["Vector"])
    bm = bump(nt, 0.4, 0.005)
    L(n.outputs["Fac"], bm.inputs["Height"])
    L(bm.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Roughness"].default_value = 0.75
    return m


def mat_planks():
    m, nt, b = new_mat("Madeira_Tabuas")
    L = nt.links.new
    tc = obj_coord(nt)
    w = nt.nodes.new("ShaderNodeTexWave")
    w.wave_type = 'BANDS'
    w.bands_direction = 'X'      # tábuas verticais
    w.inputs["Scale"].default_value = 4.5
    w.inputs["Distortion"].default_value = 0.4
    w.inputs["Detail"].default_value = 0
    L(tc, w.inputs["Vector"])
    col = ramp(nt, [(0.0, (0.008, 0.005, 0.003)),
                    (0.22, (0.08, 0.05, 0.03)),
                    (1.0, (0.20, 0.12, 0.07))])
    L(w.outputs["Fac"], col.inputs["Fac"])
    L(col.outputs["Color"], b.inputs["Base Color"])
    bm = bump(nt, 0.6, 0.01)
    L(w.outputs["Fac"], bm.inputs["Height"])
    L(bm.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Roughness"].default_value = 0.8
    return m


def mat_roof():
    m, nt, b = new_mat("Telhado")
    L = nt.links.new
    tc = obj_coord(nt)
    br = nt.nodes.new("ShaderNodeTexBrick")
    br.inputs["Color1"].default_value = (0.30, 0.10, 0.05, 1)
    br.inputs["Color2"].default_value = (0.45, 0.18, 0.09, 1)
    br.inputs["Mortar"].default_value = (0.04, 0.025, 0.02, 1)
    br.inputs["Scale"].default_value = 4.0
    br.inputs["Mortar Size"].default_value = 0.02
    br.inputs["Brick Width"].default_value = 0.5
    br.inputs["Row Height"].default_value = 0.6
    L(tc, br.inputs["Vector"])
    L(br.outputs["Color"], b.inputs["Base Color"])
    bm = bump(nt, 0.7, 0.02)
    L(br.outputs["Fac"], bm.inputs["Height"])
    L(bm.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Roughness"].default_value = 0.85
    return m


def mat_grass():
    m, nt, b = new_mat("Grama")
    L = nt.links.new
    tc = obj_coord(nt)
    n1 = noise(nt, 0.6, 8, 0.6)
    L(tc, n1.inputs["Vector"])
    col = ramp(nt, [(0.0, (0.04, 0.07, 0.02)),
                    (0.5, (0.11, 0.16, 0.05)),
                    (1.0, (0.20, 0.17, 0.08))])
    L(n1.outputs["Fac"], col.inputs["Fac"])
    L(col.outputs["Color"], b.inputs["Base Color"])
    n2 = noise(nt, 120, 4)
    L(tc, n2.inputs["Vector"])
    bm = bump(nt, 0.6, 0.02)
    L(n2.outputs["Fac"], bm.inputs["Height"])
    L(bm.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Roughness"].default_value = 1.0
    return m


def mat_simple(name, color, rough, metal=0.0):
    m, nt, b = new_mat(name)
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m


MAT_STONE = mat_stone()
MAT_PATH = mat_stone("Pedra_Caminho", 3.0)
MAT_PLASTER = mat_plaster()
MAT_BEAM = mat_wood_beam()
MAT_PLANKS = mat_planks()
MAT_ROOF = mat_roof()
MAT_GRASS = mat_grass()
MAT_IRON = mat_simple("Ferro", (0.03, 0.03, 0.035), 0.45, 1.0)
MAT_GLASS = mat_simple("Vidro", (0.02, 0.035, 0.045), 0.05, 0.3)
MAT_DARK = mat_simple("Escuro", (0.01, 0.01, 0.01), 0.9)


# ================================================================= HELPERS
def add_bevel(o, width):
    bv = o.modifiers.new("Bevel", 'BEVEL')
    bv.width = width
    bv.segments = 2
    bv.limit_method = 'ANGLE'


def box(name, loc, dim, mat, rot=(0, 0, 0), parent=None, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = dim
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.rotation_euler = rot
    o.data.materials.append(mat)
    if bevel > 0:
        add_bevel(o, bevel)
    if parent:
        o.parent = parent
    return o


def cyl(name, loc, r, depth, mat, rot=(0, 0, 0), parent=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=r, depth=depth,
                                        location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(mat)
    if parent:
        o.parent = parent
    return o


def torus(name, loc, major, minor, mat, rot=(0, 0, 0), parent=None):
    bpy.ops.mesh.primitive_torus_add(location=loc, rotation=rot,
                                     major_radius=major, minor_radius=minor,
                                     major_segments=32, minor_segments=8)
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(mat)
    if parent:
        o.parent = parent
    return o


def beam(name, a, b, size, mat=None):
    """Viga de seção quadrada indo do ponto a até o ponto b (coords de mundo)."""
    mat = mat or MAT_BEAM
    a, b = Vector(a), Vector(b)
    d = b - a
    bpy.ops.mesh.primitive_cube_add(size=1, location=(a + b) / 2)
    o = bpy.context.active_object
    o.name = name
    o.scale = (size, size, d.length)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d)
    o.data.materials.append(mat)
    add_bevel(o, 0.008)
    return o


def local_frame(name, loc, rot_z):
    e = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(e)
    e.location = loc
    e.rotation_euler = (0, 0, rot_z)
    return e


# ================================================================= ESTRUTURA
# --- base de pedra
box("Base_Pedra", (0, 0, Z_B / 2), (2 * XW + 0.2, 5.0, Z_B), MAT_STONE, bevel=0.03)

# --- paredes de reboco
box("Parede_Terreo", (0, (Y_FRONT_G + Y_BACK) / 2, (Z_B + Z_F) / 2),
    (2 * XW, Y_BACK - Y_FRONT_G, Z_F - Z_B), MAT_PLASTER)
box("Parede_Andar", (0, Y0, (Z_F + Z_E) / 2),
    (2 * XW, Y_BACK - Y_FRONT_U, Z_E - Z_F), MAT_PLASTER)

# --- balanço (jetty): viga frontal, vigotas e mãos-francesas
box("Jetty_Viga", (0, Y_FRONT_U + 0.11, Z_F - 0.14), (2 * XW, 0.22, 0.28),
    MAT_BEAM, bevel=0.01)
for i, x in enumerate([-2.6 + k * 0.65 for k in range(9)]):
    box(f"Jetty_Vigota_{i}", (x, Y_FRONT_U + 0.27, Z_F - 0.1), (0.15, 0.55, 0.2),
        MAT_BEAM, bevel=0.008)
for s in (-1, 1):
    beam(f"Jetty_Braco_{s}", (s * (XW - 0.05), Y_FRONT_G - 0.02, Z_F - 0.55),
         (s * (XW - 0.05), Y_FRONT_U + 0.05, Z_F - 0.1), 0.12)


# --- enxaimel (madeira aparente) nas paredes
def timber_wall(name, A, B, n, z0, z1, posts, panels):
    A = Vector((A[0], A[1], 0))
    B = Vector((B[0], B[1], 0))
    n = Vector((n[0], n[1], 0))
    off = n * 0.02

    def P(t, z):
        p = A + (B - A) * t + off
        return (p.x, p.y, z)

    beam(name + "_Soleira", P(0, z0 + 0.08), P(1, z0 + 0.08), 0.15)
    beam(name + "_Frechal", P(0, z1 - 0.08), P(1, z1 - 0.08), 0.15)
    for k, t in enumerate(posts):
        beam(f"{name}_Pilar_{k}", P(t, z0), P(t, z1), 0.15)
    for i in range(len(posts) - 1):
        kind = panels.get(i, 'diag')
        t0, t1 = posts[i], posts[i + 1]
        if kind == 'diag':
            if i % 2 == 0:
                a, b = P(t0, z0 + 0.08), P(t1, z1 - 0.08)
            else:
                a, b = P(t1, z0 + 0.08), P(t0, z1 - 0.08)
            beam(f"{name}_Escora_{i}", a, b, 0.11)
        elif kind == 'plain':
            zm = (z0 + z1) / 2
            beam(f"{name}_Travessa_{i}", P(t0, zm), P(t1, zm), 0.11)


# --- janelas com moldura, caixilho, peitoril e venezianas
def window(name, A, B, t, n, zc, w, h, shutters=True):
    A = Vector((A[0], A[1], 0))
    B = Vector((B[0], B[1], 0))
    p = A + (B - A) * t
    rot = math.atan2(n[1], n[0]) - math.pi / 2
    e = local_frame(name, (p.x, p.y, zc), rot)
    th = 0.07
    box(name + "_vidro", (0, -0.03, 0), (w, 0.03, h), MAT_GLASS, parent=e)
    box(name + "_mold_s", (0, 0.02, h / 2 + th / 2), (w + 2 * th, 0.1, th), MAT_BEAM, parent=e)
    box(name + "_mold_i", (0, 0.02, -h / 2 - th / 2), (w + 2 * th, 0.1, th), MAT_BEAM, parent=e)
    box(name + "_mold_e", (-(w / 2 + th / 2), 0.02, 0), (th, 0.1, h), MAT_BEAM, parent=e)
    box(name + "_mold_d", ((w / 2 + th / 2), 0.02, 0), (th, 0.1, h), MAT_BEAM, parent=e)
    box(name + "_cx_v", (0, 0.0, 0), (0.03, 0.05, h), MAT_BEAM, parent=e)
    box(name + "_cx_h", (0, 0.0, 0), (w, 0.05, 0.03), MAT_BEAM, parent=e)
    box(name + "_peitoril", (0, 0.09, -h / 2 - th - 0.03), (w + 0.3, 0.2, 0.06),
        MAT_STONE, parent=e, bevel=0.01)
    if shutters:
        sw = 0.28
        for s in (-1, 1):
            x = s * (w / 2 + th + sw / 2 + 0.01)
            box(f"{name}_veneziana_{s}", (x, 0.045, 0), (sw, 0.05, h + 0.1),
                MAT_PLANKS, parent=e, bevel=0.005)
            for z in (-h / 4, h / 4):
                box(f"{name}_dobradica_{s}_{z:.1f}", (x, 0.077, z), (sw, 0.015, 0.05),
                    MAT_IRON, parent=e)


# --- paredes do térreo
G0, G1 = Z_B, Z_F
timber_wall("FrenteT", (-XW, Y_FRONT_G), (XW, Y_FRONT_G), (0, -1), G0, G1,
            [0, 0.25, 0.75, 1], {0: 'window', 1: 'door', 2: 'window'})
window("Jan_FrenteT_E", (-XW, Y_FRONT_G), (XW, Y_FRONT_G), 0.125, (0, -1), 2.2, 0.6, 0.9)
window("Jan_FrenteT_D", (-XW, Y_FRONT_G), (XW, Y_FRONT_G), 0.875, (0, -1), 2.2, 0.6, 0.9)

timber_wall("TrasT", (-XW, Y_BACK), (XW, Y_BACK), (0, 1), G0, G1,
            [0, 0.25, 0.5, 0.75, 1], {1: 'window'})
window("Jan_TrasT", (-XW, Y_BACK), (XW, Y_BACK), 0.375, (0, 1), 2.2, 0.6, 0.9)

third = [0, 1 / 3, 2 / 3, 1]
timber_wall("EsqT", (-XW, Y_FRONT_G), (-XW, Y_BACK), (-1, 0), G0, G1, third, {1: 'window'})
window("Jan_EsqT", (-XW, Y_FRONT_G), (-XW, Y_BACK), 0.5, (-1, 0), 2.2, 0.6, 0.9)

timber_wall("DirT", (XW, Y_FRONT_G), (XW, Y_BACK), (1, 0), G0, G1, third, {})

# --- paredes do andar de cima
U0, U1 = Z_F, Z_E
five = [0, 0.25, 0.5, 0.75, 1]
timber_wall("FrenteA", (-XW, Y_FRONT_U), (XW, Y_FRONT_U), (0, -1), U0, U1,
            five, {0: 'window', 3: 'window'})
window("Jan_FrenteA_E", (-XW, Y_FRONT_U), (XW, Y_FRONT_U), 0.125, (0, -1), 4.7, 0.6, 0.95)
window("Jan_FrenteA_D", (-XW, Y_FRONT_U), (XW, Y_FRONT_U), 0.875, (0, -1), 4.7, 0.6, 0.95)

timber_wall("TrasA", (-XW, Y_BACK), (XW, Y_BACK), (0, 1), U0, U1,
            five, {1: 'window', 2: 'window'})
window("Jan_TrasA_1", (-XW, Y_BACK), (XW, Y_BACK), 0.375, (0, 1), 4.7, 0.6, 0.95)
window("Jan_TrasA_2", (-XW, Y_BACK), (XW, Y_BACK), 0.625, (0, 1), 4.7, 0.6, 0.95)

timber_wall("EsqA", (-XW, Y_FRONT_U), (-XW, Y_BACK), (-1, 0), U0, U1,
            five, {1: 'window', 2: 'window'})
window("Jan_EsqA_1", (-XW, Y_FRONT_U), (-XW, Y_BACK), 0.375, (-1, 0), 4.7, 0.6, 0.95)
window("Jan_EsqA_2", (-XW, Y_FRONT_U), (-XW, Y_BACK), 0.625, (-1, 0), 4.7, 0.6, 0.95)

timber_wall("DirA", (XW, Y_FRONT_U), (XW, Y_BACK), (1, 0), U0, U1, five, {})

# ================================================================= PORTA
door = local_frame("Porta", (0, Y_FRONT_G, Z_B), math.pi)
cyl("Porta_Arco_Moldura", (0, 0.0, 1.6), 0.69, 0.12, MAT_BEAM,
    rot=(math.pi / 2, 0, 0), parent=door)
box("Porta_Moldura", (0, 0.0, 0.8), (1.38, 0.12, 1.6), MAT_BEAM, parent=door)
cyl("Porta_Arco", (0, 0.08, 1.6), 0.55, 0.08, MAT_PLANKS,
    rot=(math.pi / 2, 0, 0), parent=door)
box("Porta_Folha", (0, 0.08, 0.8), (1.1, 0.08, 1.6), MAT_PLANKS, parent=door)
for z in (0.35, 1.25):
    box(f"Porta_Ferragem_{z}", (0, 0.125, z), (0.95, 0.018, 0.1), MAT_IRON, parent=door)
torus("Porta_Aldrava", (0.32, 0.14, 0.85), 0.06, 0.012, MAT_IRON,
      rot=(math.pi / 2, 0, 0), parent=door)
box("Porta_Soleira", (0, 0.05, -0.04), (1.5, 0.35, 0.08), MAT_STONE, parent=door)

# degraus de pedra
box("Degrau_1", (0, -2.75, Z_B / 2), (1.9, 0.5, Z_B), MAT_STONE, bevel=0.02)
box("Degrau_2", (0, -3.25, 0.225), (2.3, 0.5, 0.45), MAT_STONE, bevel=0.02)

# ================================================================= EMPENA E TELHADO
def gable(sign):
    verts = [(0, Y0 - HS, Z_E), (0, Y0 + HS, Z_E), (0, Y0, Z_E + HR)]
    me = bpy.data.meshes.new("Empena_Mesh")
    me.from_pydata(verts, [], [(0, 1, 2)])
    me.update()
    o = bpy.data.objects.new(f"Empena_{sign}", me)
    bpy.context.collection.objects.link(o)
    o.location = (sign * XW, 0, 0)
    sol = o.modifiers.new("Solid", 'SOLIDIFY')
    sol.thickness = 0.2
    sol.offset = 0
    me.materials.append(MAT_PLASTER)
    # madeiramento da empena
    x = sign * (XW + 0.11)
    beam(f"Empena_Pilar_{sign}", (x, Y0, Z_E), (x, Y0, Z_E + HR - 0.15), 0.13)
    z1 = Z_E + 1.0
    hw1 = HS * (1 - 1.0 / HR) - 0.1
    beam(f"Empena_Travessa1_{sign}", (x, Y0 - hw1, z1), (x, Y0 + hw1, z1), 0.12)
    z2 = Z_E + 1.9
    hw2 = HS * (1 - 1.9 / HR) - 0.1
    beam(f"Empena_Travessa2_{sign}", (x, Y0 - hw2, z2), (x, Y0 + hw2, z2), 0.11)
    for s in (-1, 1):
        beam(f"Empena_Escora_{sign}_{s}", (x, Y0 + s * 1.2, Z_E), (x, Y0, z1), 0.1)


gable(-1)
gable(1)

E_OVER, TH = 0.5, 0.22
L1 = HS / math.cos(PITCH)
LTOT = L1 + E_OVER + 0.1
T_C = (L1 + 0.1 - E_OVER) / 2
SLAB_X = 2 * XW + 2 * E_OVER

for sgn, nm in ((-1, "Frente"), (1, "Tras")):
    ey = Y0 + sgn * HS
    dy, dz = -sgn * math.cos(PITCH), math.sin(PITCH)
    ny, nz = sgn * math.sin(PITCH), math.cos(PITCH)
    cy = ey + dy * T_C - ny * TH / 2
    cz = Z_E + dz * T_C - nz * TH / 2
    rx = -sgn * PITCH
    box(f"Telhado_{nm}", (0, cy, cz), (SLAB_X, LTOT, TH), MAT_ROOF,
        rot=(rx, 0, 0), bevel=0.01)
    for sx in (-1, 1):
        box(f"Tabeira_{nm}_{sx}", (sx * (XW + E_OVER - 0.025), cy, cz),
            (0.05, LTOT, 0.3), MAT_BEAM, rot=(rx, 0, 0), bevel=0.006)

box("Cumeeira", (0, Y0, Z_E + HR), (SLAB_X + 0.1, 0.22, 0.22), MAT_BEAM,
    rot=(math.radians(45), 0, 0), bevel=0.01)

# ================================================================= CHAMINÉ
CX = XW + 0.45
box("Chamine_A", (CX, Y0, 2.2), (1.0, 1.7, 4.4), MAT_STONE, bevel=0.03)
box("Chamine_B", (CX - 0.05, Y0, 5.4), (0.8, 1.2, 2.0), MAT_STONE, bevel=0.03)
box("Chamine_C", (CX - 0.1, Y0, 8.1), (0.7, 1.0, 3.5), MAT_STONE, bevel=0.03)
box("Chamine_Topo", (CX - 0.1, Y0, 9.95), (0.95, 1.25, 0.18), MAT_STONE, bevel=0.02)
box("Chamine_Boca", (CX - 0.1, Y0, 10.05), (0.5, 0.8, 0.05), MAT_DARK)

# ================================================================= AMBIENTE
# chão
bpy.ops.mesh.primitive_plane_add(size=80, location=(0, 0, 0))
ground = bpy.context.active_object
ground.name = "Chao"
ground.data.materials.append(MAT_GRASS)

# caminho de pedras até a porta
for i in range(10):
    w = 0.7 + 0.4 * random.random()
    box(f"Caminho_{i}", (random.uniform(-0.5, 0.5), -4.0 - i * 0.7, 0.03),
        (w, 0.55, 0.1), MAT_PATH,
        rot=(0, 0, math.radians(random.uniform(-15, 15))), bevel=0.02)

# barril e caixote
cyl("Barril", (-1.9, -3.3, 0.43), 0.33, 0.86, MAT_PLANKS)
for z in (0.2, 0.65):
    torus(f"Barril_Aro_{z}", (-1.9, -3.3, z), 0.335, 0.02, MAT_IRON)
box("Caixote", (2.2, -3.1, 0.25), (0.6, 0.6, 0.5), MAT_PLANKS,
    rot=(0, 0, math.radians(12)), bevel=0.01)

# ================================================================= CENA
parts = [o for o in bpy.data.objects
         if o.parent is None and o.name != "Chao"]
root = bpy.data.objects.new("Casa_Medieval", None)
bpy.context.collection.objects.link(root)
for p in parts:
    p.parent = root

# câmera
cam_data = bpy.data.cameras.new("Camera")
cam_data.lens = 38
cam = bpy.data.objects.new("Camera", cam_data)
bpy.context.collection.objects.link(cam)
cam.location = (11, -14, 6.5)
target = bpy.data.objects.new("Alvo", None)
target.location = (0, 0, 4.2)
bpy.context.collection.objects.link(target)
tr = cam.constraints.new('TRACK_TO')
tr.target = target
tr.track_axis = 'TRACK_NEGATIVE_Z'
tr.up_axis = 'UP_Y'
bpy.context.scene.camera = cam

# sol
sun_data = bpy.data.lights.new("Sol", 'SUN')
sun_data.energy = 4.0
sun_data.angle = math.radians(3)
sun_data.color = (1.0, 0.92, 0.8)
sun = bpy.data.objects.new("Sol", sun_data)
bpy.context.collection.objects.link(sun)
sun.rotation_euler = (math.radians(50), 0, math.radians(35))

# céu
scene = bpy.context.scene
world = scene.world or bpy.data.worlds.new("World")
scene.world = world
try:
    world.use_nodes = True
except Exception:
    pass
wnt = world.node_tree
for n in list(wnt.nodes):
    wnt.nodes.remove(n)
bg = wnt.nodes.new("ShaderNodeBackground")
wout = wnt.nodes.new("ShaderNodeOutputWorld")
wnt.links.new(bg.outputs["Background"], wout.inputs["Surface"])
bg.inputs["Color"].default_value = (0.45, 0.60, 0.80, 1)
bg.inputs["Strength"].default_value = 0.9

# render
scene.render.engine = 'CYCLES'
scene.cycles.samples = 96
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
try:
    scene.view_settings.view_transform = 'AgX'
except TypeError:
    scene.view_settings.view_transform = 'Filmic'

print("Casa medieval criada! F12 para renderizar.")

# ------------- opcional: exportar (descomente) -------------
# import os
# bpy.ops.wm.save_as_mainfile(filepath=os.path.expanduser("~/casa_medieval.blend"))
# bpy.ops.export_scene.gltf(filepath=os.path.expanduser("~/casa_medieval.glb"))
