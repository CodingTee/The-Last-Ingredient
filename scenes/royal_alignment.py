"""Subpixel stovetop alignment at render time; source rasters stay unchanged."""
import arcade
from arcade import gl

SOURCE_SHIFT = 2.1
VERTEX = """#version 330
uniform WindowBlock { mat4 projection; mat4 view; } window;
uniform vec4 rect;
out vec2 uv;
void main(){
 vec2 corners[4]=vec2[4](vec2(0,0),vec2(0,1),vec2(1,0),vec2(1,1));
 uv=corners[gl_VertexID];
 vec2 pos=rect.xy+vec2(uv.x-.5,.5-uv.y)*rect.zw;
 gl_Position=window.projection*window.view*vec4(pos,0,1);
}"""
FRAGMENT = """#version 330
uniform sampler2D scene;
uniform vec4 source_crop;
uniform float shift_px;
in vec2 uv;
out vec4 f_color;
void main(){
 vec2 p=source_crop.xy+uv*source_crop.zw;
 float mask=smoothstep(260.,290.,p.x)*(1.-smoothstep(502.,525.,p.x))
           *smoothstep(431.,437.,p.y)*(1.-smoothstep(454.,459.,p.y));
 vec2 sample_uv=uv-vec2(shift_px*mask/source_crop.z,0.);
 f_color=texture(scene,sample_uv);
}"""


class StovetopAlignment:
    def __init__(self, ctx):
        self.ctx = ctx
        self.program = ctx.program(vertex_shader=VERTEX, fragment_shader=FRAGMENT)
        self.program["scene"] = 0
        self.program["shift_px"] = SOURCE_SHIFT
        self.textures = {}

    def draw(self, texture, x, y, width, height):
        scale = min(width / texture.width, height / texture.height)
        width, height = texture.width * scale, texture.height * scale
        key = str(texture.file_path)
        if key not in self.textures:
            gpu = self.ctx.texture((texture.width, texture.height), components=4,
                                 data=texture.image.convert("RGBA").tobytes())
            gpu.filter = (gl.LINEAR, gl.LINEAR)
            self.textures[key] = gpu
        self.textures[key].use(0)
        self.program["rect"] = (x, y, width, height)
        self.program["source_crop"] = (0, 0, texture.width, texture.height)
        self.ctx.geometry().render(self.program, mode=gl.TRIANGLE_STRIP, vertices=4)
