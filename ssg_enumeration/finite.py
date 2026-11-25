"""Normal subgroups, quotients and certified finite-group isomorphisms."""
from itertools import product


def element_order(table, a):
    x = 0
    for n in range(1,len(table)+1):
        x = table[x][a]
        if x == 0:
            return n
    raise ValueError("Not a finite group table.")


def generated_subgroup(table, generators):
    result = {0}
    pending = [0]
    while pending:
        x = pending.pop()
        for g in generators:
            y = table[x][g]
            if y not in result:
                result.add(y)
                pending.append(y)
    return frozenset(result)


def normal_closure(table, generators):
    inv = [row.index(0) for row in table]
    conjugates = {table[table[p][g]][inv[p]] for p in range(len(table)) for g in generators}
    return generated_subgroup(table,conjugates)


def normal_subgroups(table):
    """Enumerate the normal-subgroup lattice by adjoining normal closures."""
    found = {frozenset({0})}
    pending = [frozenset({0})]
    while pending:
        h = pending.pop()
        for a in range(len(table)):
            if a not in h:
                k = normal_closure(table,tuple(h)+(a,))
                if k not in found:
                    found.add(k)
                    pending.append(k)
    return tuple(sorted(found,key=lambda h:(len(h),tuple(sorted(h)))))


def quotient_group(table, normal):
    if normal_closure(table,normal) != frozenset(normal):
        raise ValueError("Subgroup must be normal.")
    cosets, projection = [],{}
    for a in range(len(table)):
        if a not in projection:
            coset = frozenset(table[a][h] for h in normal)
            projection.update({g:len(cosets) for g in coset})
            cosets.append(coset)
    reps = [min(c) for c in cosets]
    qt = tuple(tuple(projection[table[a][b]] for b in reps) for a in reps)
    return qt,tuple(projection[g] for g in range(len(table)))


def small_generating_set(table):
    chosen = []
    reached = frozenset({0})
    while len(reached) < len(table):
        a = max((a for a in range(len(table)) if a not in reached),
                key=lambda a:len(generated_subgroup(table,chosen+[a])))
        chosen.append(a)
        reached = generated_subgroup(table,chosen)
    return tuple(chosen)


def find_isomorphism(source, target):
    """One bijection of full multiplication tables, or None (no order-only guesses)."""
    if len(source) != len(target):
        return None
    orders_s = [element_order(source,a) for a in range(len(source))]
    orders_t = [element_order(target,a) for a in range(len(target))]
    if sorted(orders_s) != sorted(orders_t):
        return None
    gens = small_generating_set(source)
    choices = [[b for b,o in enumerate(orders_t) if o == orders_s[a]] for a in gens]
    for images in product(*choices):
        if len(generated_subgroup(target,images)) != len(target):
            continue
        mapping = {0:0}
        pending = [0]
        valid = True
        while pending and valid:
            x = pending.pop()
            for a,b in zip(gens,images):
                y,z = source[x][a],target[mapping[x]][b]
                if y in mapping:
                    if mapping[y] != z:
                        valid = False
                        break
                else:
                    mapping[y] = z
                    pending.append(y)
        if valid and len(mapping) == len(source) and len(set(mapping.values())) == len(source):
            phi = tuple(mapping[i] for i in range(len(source)))
            if all(phi[source[a][b]] == target[phi[a]][phi[b]] for a,b in product(range(len(source)),repeat=2)):
                return phi
    return None

