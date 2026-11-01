"""Minimal APEXlang emitter.

Node model (mirrors the APEXlang grammar in the apexlang-inventory skill):
  Comp(kind, ident, *members)  -> component declaration  `kind ident (` ... `)`
  ('name', 'value')            -> scalar property         `name: value`
  ('name', G(...))             -> property group          `name {` ... `}`
  ('name', O(...))             -> complex property        `name: {` ... `}`
  ('name', A([...]))           -> array property          `name: [` ... `]`
  ('name', ML('sql', text))    -> multiline string        name:\n ```sql ... ```

Every property / array value / member is emitted on its own physical line.
"""

IND = "    "


class G:
    def __init__(self, *members):
        self.members = [m for m in members if m is not None]


class O:
    def __init__(self, *members):
        self.members = [m for m in members if m is not None]


class A:
    def __init__(self, values):
        self.values = list(values)


class ML:
    def __init__(self, lang, text):
        self.lang = lang
        self.text = text.strip("\n")


class Comp:
    def __init__(self, kind, ident, *members):
        self.kind = kind
        self.ident = ident
        self.members = [m for m in members if m is not None]


def _scalar(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    s = str(v)
    if "\n" in s:
        raise ValueError("scalar contains newline: %r" % s)
    return s


def _emit_members(members, level, out, in_object=False):
    for m in members:
        if isinstance(m, Comp):
            out.append("")
            _emit_comp(m, level, out)
            continue
        name, val = m
        pad = IND * level
        if isinstance(val, G):
            if in_object:
                raise ValueError("group inside object: %s" % name)
            if not val.members:
                continue
            out.append("%s%s {" % (pad, name))
            _emit_members(val.members, level + 1, out)
            out.append("%s}" % pad)
        elif isinstance(val, O):
            out.append("%s%s: {" % (pad, name))
            _emit_members(val.members, level + 1, out, in_object=True)
            out.append("%s}" % pad)
        elif isinstance(val, A):
            if len(val.values) == 1:
                out.append("%s%s: %s" % (pad, name, _scalar(val.values[0])))
            else:
                out.append("%s%s: [" % (pad, name))
                for v in val.values:
                    out.append("%s%s" % (IND * (level + 1), _scalar(v)))
                out.append("%s]" % pad)
        elif isinstance(val, ML):
            if "```" in val.text:
                raise ValueError("multiline contains fence")
            out.append("%s%s:" % (pad, name))
            ipad = IND * (level + 1)
            out.append("%s```%s" % (ipad, val.lang))
            for line in val.text.split("\n"):
                out.append(ipad + line)
            out.append("%s```" % ipad)
        elif val is None:
            continue
        else:
            out.append("%s%s: %s" % (pad, name, _scalar(val)))


def _emit_comp(c, level, out):
    pad = IND * level
    head = c.kind if c.ident is None else "%s %s" % (c.kind, c.ident)
    out.append("%s%s (" % (pad, head))
    _emit_members(c.members, level + 1, out)
    if c.members and isinstance(c.members[-1], Comp):
        out.append("")
    out.append("%s)" % pad)


def render(*comps):
    out = []
    for i, c in enumerate(comps):
        if i:
            out.append("")
        _emit_comp(c, 0, out)
    return "\n".join(out) + "\n"
