"""Fit a deliberately untucked lower shirt outside the trousers, per shape key.

Boundary smoothing shortens helper loops. Flattening those points afterwards can
pull the hem through the trousers. Keep the full shared helper topology and weights,
but build a smooth outer hem against each actual trouser morph, not an arbitrary
z-fighting offset in the renderer. This therefore also survives GLB export.
"""
from mathutils import Vector
from mathutils.bvhtree import BVHTree

def fit_waist(shirt, pants):
    triangles=[list(p.vertices) for p in pants.data.polygons]
    basis=shirt.data.shape_keys.key_blocks[0]
    for key in shirt.data.shape_keys.key_blocks:
        other=pants.data.shape_keys.key_blocks.get(key.name) or pants.data.shape_keys.key_blocks[0]
        tree=BVHTree.FromPolygons([v.co for v in other.data],triangles,all_triangles=False)
        for i,v in enumerate(key.data):
            z=basis.data[i].co.z
            if z>=1.055: continue
            # The 8 cm transition removes the pinched hard corner at the waist.
            blend=max(0,min(1,(1.055-z)/.065)); blend=blend*blend*(3-2*blend)
            origin=Vector((0,0,min(.970,max(.959,v.co.z))))
            direction=Vector((v.co.x,v.co.y,0)).normalized()
            hit,normal,index,distance=tree.ray_cast(origin,direction,.5)
            if hit is None: raise ValueError('Trousers must enclose the waist')
            current=Vector((v.co.x,v.co.y,0)).length
            # > 1 cm clearance leaves room for piecewise-linear triangles at
            # different ring heights, shape interpolation, and posed skinning.
            target=max(current,distance+.014)
            radius=current+(target-current)*blend
            v.co.x=direction.x*radius; v.co.y=direction.y*radius
    for v,k in zip(shirt.data.vertices,basis.data): v.co=k.co
    shirt.data.update()
