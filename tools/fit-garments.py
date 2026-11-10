"""Fit a deliberately untucked lower shirt outside the trousers, per shape key.

Boundary smoothing shortens helper loops. Flattening those points afterwards can
pull the hem through the trousers. Keep the full shared helper topology and weights,
but build a smooth outer hem against each actual trouser morph, not an arbitrary
z-fighting offset in the renderer. This therefore also survives GLB export.
"""
from mathutils import Vector
from mathutils.bvhtree import BVHTree

def level_hem(shirt, height=.955, transition=1.055):
    """A level boundary and smooth, noncollapsed interior rows for every shape.

    Solve a harmonic height field on the existing lower-shirt topology. Only
    actual boundary vertices are pinned to the hem; the upper row stays fixed.
    Keeping vertex correspondence preserves all UVs and normalized skin weights.
    """
    import numpy as np
    edges={}
    neighbors={i:set() for i in range(len(shirt.data.vertices))}
    for polygon in shirt.data.polygons:
        for a,b in polygon.edge_keys:
            edges[(a,b)]=edges.get((a,b),0)+1
            neighbors[a].add(b);neighbors[b].add(a)
    basis=shirt.data.shape_keys.key_blocks[0]
    # Find whole boundary loops. The lowest sleeve vertices can fall inside
    # the same height band, so selecting vertices by height alone stretches them.
    border={}
    for (a,b),count in edges.items():
        if count==1:border.setdefault(a,set()).add(b);border.setdefault(b,set()).add(a)
    remaining=set(border);loops=[]
    while remaining:
        loop=set();pending=[next(iter(remaining))]
        while pending:
            i=pending.pop()
            if i in loop:continue
            loop.add(i);pending.extend(border[i]-loop)
        remaining-=loop;loops.append(loop)
    boundary=min(loops,key=lambda loop:sum(basis.data[i].co.z for i in loop)/len(loop))
    assert max(basis.data[i].co.z for i in boundary)<transition, 'Expected a complete lower hem loop'
    band=set(boundary);pending=list(boundary)
    while pending:
        i=pending.pop()
        for j in neighbors[i]-band:
            if basis.data[j].co.z<transition:band.add(j);pending.append(j)
    interior=sorted(band-boundary)
    lookup={i:j for j,i in enumerate(interior)}
    matrix=np.zeros((len(interior),len(interior)))
    for i,row in lookup.items():
        matrix[row,row]=len(neighbors[i])
        for j in neighbors[i]:
            if j in lookup:matrix[row,lookup[j]]-=1
    for key in shirt.data.shape_keys.key_blocks:
        rhs=np.zeros(len(interior))
        for i in boundary:key.data[i].co.z=height
        for i,row in lookup.items():
            rhs[row]=sum(key.data[j].co.z for j in neighbors[i] if j not in lookup)
        values=np.linalg.solve(matrix,rhs)
        for i,row in lookup.items():key.data[i].co.z=float(values[row])
    for vertex,point in zip(shirt.data.vertices,basis.data):vertex.co=point.co
    shirt.data.update()

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
