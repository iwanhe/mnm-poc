#!/usr/bin/env python3
"""Scaffold generator untuk aplikasi APEXlang MBMS MVP (APEX 26.2).

Menghasilkan folder apex/mbms dari spesifikasi di file ini. Dipakai sekali untuk
baseline; setelah aplikasi di-import dan diubah lewat Page Designer, export ulang
dari APEX menjadi sumber kebenaran (Blueprint 8.5 langkah 5).

    python3 tools/apexgen/gen_mbms.py [output_dir]
"""
import os
import shutil
import sys

from apx import A, Comp, G, ML, O, render

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(ROOT, "apex", "mbms")
EXAMPLE0 = os.path.join(ROOT, ".claude", "skills", "apexlang", "26.2",
                        "apexlang-example-applications", "assets", "example-0")

FILES = {}


def put(rel, content):
    FILES[rel] = content


# =============================================================================
# Common fragments
# =============================================================================
MONEY = "999G999G999G999G990"
QTY = "999G999G999G990D99"
EDIT_ICON = '<span aria-label="Edit"><span class="fa fa-edit" aria-hidden="true" title="Edit"></span></span>'


def cond_expr(expr):
    return ("serverSideCondition", G(("type", "expression"), ("plsqlExpression", expr)))


def breadcrumb_region(seq=10):
    return Comp("region", "breadcrumb",
                ("name", "Breadcrumb"),
                ("type", "breadcrumb"),
                ("source", G(("breadcrumb", "@breadcrumb"))),
                ("layout", G(("sequence", seq), ("slot", "breadcrumbBar"))),
                ("appearance", G(("template", "@/title-bar"),
                                 ("templateOptions", A(["#DEFAULT#", "t-BreadcrumbRegion--useBreadcrumbTitle"])))),
                ("componentAppearance", G(("breadcrumbTemplate", "@/breadcrumb"),
                                          ("templateOptions", "#DEFAULT#"))))


def val_expr(ident, name, seq, expr, msg, item_name, requests=None):
    return Comp("validation", ident,
                ("name", name),
                ("execution", G(("sequence", seq))),
                ("validation", G(("type", "expression"), ("plsqlExpression", expr))),
                ("error", G(("errorMessage", msg),
                            ("displayLocation", "inlineWithFieldAndInNotification"),
                            ("associatedItem", "@" + item_name))),
                ("serverSideCondition", G(("type", "requestIsContainedInValue"), ("value", requests)))
                if requests else None)


def refresh_on_dialog_close(region_id):
    return Comp("dynamicAction", "edit-report-dialog-closed",
                ("name", "Edit Report - Dialog Closed"),
                ("execution", G(("sequence", 10))),
                ("when", G(("event", "apexafterclosedialog"),
                           ("selectionType", "region"),
                           ("region", "@" + region_id))),
                Comp("action", "native-refresh",
                     ("action", "refresh"),
                     ("affectedElements", G(("selectionType", "region"), ("region", "@" + region_id))),
                     ("execution", G(("sequence", 10), ("fireOnInit", False)))))


# =============================================================================
# Interactive report page
# =============================================================================
def ir_column(name, heading, kind, seq, alias):
    members = []
    ctype = "hidden" if kind == "hidden" else "plainText"
    members.append(("type", ctype))
    head = [("heading", heading)]
    lay = [("sequence", seq)]
    if kind in ("money", "qty", "num", "pct"):
        head.append(("alignment", "end"))
        lay.append(("columnAlignment", "end"))
    members.append(("heading", G(*head)))
    members.append(("layout", G(*lay)))
    if kind == "money":
        members.append(("appearance", G(("formatMask", MONEY))))
    elif kind == "qty":
        members.append(("appearance", G(("formatMask", QTY))))
    dtype = {"money": "number", "qty": "number", "num": "number", "pct": "number",
             "hidden": "number", "date": "date"}.get(kind, "varchar2")
    members.append(("source", G(("dataType", dtype))))
    members.append(("advanced", G(("endUserAlias", alias))))
    return Comp("column", name, *members)


def _alias(i):
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def ir_page(num, name, alias, group, region_id, sql, cols, form_page=None, pk=None,
            create=True, auth=None, create_auth=None, sort_col=None, sort_desc=False,
            before_regions=(), title=None, help_text=None, column_links=()):
    """cols: list of (COLUMN, heading, kind). kind: text|num|qty|money|pct|date|hidden"""
    col_comps = []
    seq_display = []
    for i, (c, h, k) in enumerate(cols):
        comp = ir_column(c, h, k, i + 1, _alias(i))
        for (lcol, target) in column_links:
            if lcol == c:
                comp.members[0] = ("type", "link")
                comp.members.append(("link", G(("target", target), ("linkText", "#%s#" % c))))
        col_comps.append(comp)
        if k != "hidden":
            seq_display.append(c)

    region_members = [
        ("name", title or name),
        ("type", "interactiveReport"),
        ("source", G(("location", "localDatabase"), ("type", "sqlQuery"), ("sqlQuery", ML("sql", sql)))),
        ("layout", G(("sequence", 20), ("slot", "body"))),
        ("appearance", G(("template", "@/interactive-report"), ("templateOptions", "#DEFAULT#"))),
    ]
    if form_page:
        region_members.append(("link", G(
            ("linkColumn", "customTarget"),
            ("target", O(("page", form_page),
                         ("items", O(("P%d_%s" % (form_page, pk), "\\#%s#\\" % pk))),
                         ("clearCache", form_page))),
            ("linkIcon", EDIT_ICON))))
    region_members += [
        ("pagination", G(("type", "rowRangesXToY"))),
        ("messages", G(("whenNoDataFound", "Tidak ada data."))),
        ("actionsMenu", G(("subscription", False))),
    ]
    region_members += col_comps
    sr = [("visibility", "primaryDefault"), ("view", G(("rowsPerPage", 50)))]
    for i, c in enumerate(seq_display):
        sr.append(Comp("displayColumn", c, ("sequence", i + 1)))
    if sort_col:
        sr.append(Comp("sort", None, ("column", sort_col),
                       ("sort", G(("sequence", 1), ("direction", "desc") if sort_desc else None))))
    region_members.append(Comp("savedReport", str(num * 1000 + 1), *sr))

    comps = [breadcrumb_region()] + list(before_regions) + [Comp("region", region_id, *region_members)]
    if form_page and create:
        btn = [("buttonName", "CREATE"), ("label", "Create"),
               ("layout", G(("sequence", 10), ("region", "@" + region_id), ("slot", "rightOfInteractiveReportSearchBar"))),
               ("appearance", G(("buttonTemplate", "@/text"), ("hot", True), ("templateOptions", "#DEFAULT#"))),
               ("behavior", G(("action", "redirectThisApp"),
                              ("target", O(("page", form_page), ("clearCache", form_page))),
                              ("warnOnUnsavedChanges", "doNotCheck")))]
        if create_auth:
            btn.append(("security", G(("authorizationScheme", "@" + create_auth))))
        comps.append(Comp("button", "create", *btn))
    if form_page:
        comps.append(refresh_on_dialog_close(region_id))

    page_members = [
        ("name", name),
        ("alias", alias),
        ("title", name),
        ("pageGroup", "@" + group) if group else None,
        ("appearance", G(("pageTemplate", "@/standard"), ("templateOptions", "#DEFAULT#"))),
        ("security", G(("authorizationScheme", "@" + auth))) if auth else None,
        ("help", G(("helpText", help_text))) if help_text else None,
    ] + comps
    return Comp("page", str(num), *page_members)


# =============================================================================
# Modal form page
# =============================================================================
def item(p, col, label, kind="text", req=False, dtype="varchar2", maxlen=None, lov=None,
         default_sql=None, default_static=None, readonly_expr=None, query_only=False,
         cascade=None, help=None, width=None, null_text="- Pilih -", min_value=None, max_value=None):
    return dict(p=p, col=col, label=label, kind=kind, req=req, dtype=dtype, maxlen=maxlen, lov=lov,
                default_sql=default_sql, default_static=default_static, readonly_expr=readonly_expr,
                query_only=query_only, cascade=cascade, help=help, width=width, null_text=null_text,
                min_value=min_value, max_value=max_value)


def form_item(spec, region_id, seq, form=True):
    p = spec["p"]
    name = "P%d_%s" % (p, spec["col"])
    kind = spec["kind"]
    t = {"text": "textField", "number": "numberField", "date": "datePicker", "textarea": "textarea",
         "select": "selectList", "display": "displayOnly", "hidden": "hidden", "switch": "switch"}[kind]
    m = [("type", t)]
    if kind != "hidden":
        m.append(("label", G(("label", spec["label"]), ("alignment", "right"))))
    if kind == "number":
        m.append(("settings", G(("numberAlignment", "end"), ("virtualKeyboard", "decimal"),
                                ("minValue", spec["min_value"]) if spec["min_value"] is not None else None,
                                ("maxValue", spec["max_value"]) if spec["max_value"] is not None else None)))
    if kind == "display":
        m.append(("settings", G(("sendOnPageSubmit", False))))
    if kind == "select":
        lov = spec["lov"]
        if lov.startswith("@"):
            lg = [("type", "sharedComponent"), ("lov", lov)]
        else:
            lg = [("type", "sqlQuery"), ("sqlQuery", lov)]
        lg += [("displayExtraValues", True), ("displayNullValue", True), ("nullDisplayValue", spec["null_text"])]
        m.append(("lov", G(*lg)))
        if spec["cascade"]:
            m.append(("cascadingLov", G(("parentItems", spec["cascade"]), ("parentRequired", False))))
    lay = [("sequence", seq), ("region", "@" + region_id), ("slot", "regionBody")]
    if kind != "hidden":
        lay.append(("alignment", "left"))
    m.append(("layout", G(*lay)))
    if kind != "hidden":
        ap = [("template", "@/required-floating" if spec["req"] else "@/optional-floating"),
              ("templateOptions", "#DEFAULT#")]
        if kind == "select":
            ap.append(("height", 1))
        elif kind == "textarea":
            ap += [("width", 60), ("height", 3)]
        elif kind in ("text", "number", "date"):
            ap.append(("width", spec["width"] or 32))
        m.append(("appearance", G(*ap)))
    val = []
    if spec["req"]:
        val.append(("valueRequired", True))
    if spec["maxlen"]:
        val.append(("maxLength", spec["maxlen"]))
    if val:
        m.append(("validation", G(*val)))
    if form:
        src = [("formRegion", "@" + region_id), ("column", spec["col"]), ("dataType", spec["dtype"])]
        if spec.get("pk"):
            src.append(("primaryKey", True))
        if spec["query_only"]:
            src.append(("queryOnly", True))
        m.append(("source", G(*src)))
    if spec["default_sql"]:
        m.append(("default", G(("type", "sqlQuerySingleValue"), ("sqlQuerySingleValue", spec["default_sql"]))))
    elif spec["default_static"] is not None:
        m.append(("default", G(("type", "static"), ("staticValue", spec["default_static"]))))
    if spec["readonly_expr"]:
        m.append(("readOnly", G(("type", "expression"), ("plsqlExpression", spec["readonly_expr"]))))
    if spec.get("pk"):
        m.append(("security", G(("sessionStateProtection", "checksumRequiredSessionLevel"))))
    if spec["help"]:
        m.append(("help", G(("inlineHelpText", spec["help"]))))
    return Comp("pageItem", name, *m)


def dialog_button(ident, name, label, seq, slot, hot=False, db_action=None, cond=None,
                  danger=False, confirm=None, validations=True):
    m = [("buttonName", name), ("label", label),
         ("layout", G(("sequence", seq), ("region", "@buttons"), ("slot", slot)))]
    if danger:
        m.append(("appearance", G(("buttonTemplate", "@/text"),
                                  ("templateOptions", A(["#DEFAULT#", "t-Button--danger", "t-Button--simple"])))))
    else:
        m.append(("appearance", G(("buttonTemplate", "@/text"), ("hot", True) if hot else None,
                                  ("templateOptions", "#DEFAULT#"))))
    beh = []
    if ident == "cancel":
        beh.append(("action", "definedByDynamicAction"))
    else:
        if not validations:
            beh.append(("executeValidations", False))
        beh.append(("warnOnUnsavedChanges", "doNotCheck"))
        if db_action:
            beh.append(("databaseAction", db_action))
        if confirm:
            beh.append(("requiresConfirmation", True))
    m.append(("behavior", G(*beh)))
    if confirm:
        m.append(("confirmation", G(("message", confirm), ("style", "danger" if danger else "information"))))
    if cond:
        m.append(cond_expr(cond))
    return Comp("button", ident, *m)


def cancel_da():
    return Comp("dynamicAction", "cancel-dialog",
                ("name", "Cancel Dialog"),
                ("execution", G(("sequence", 10))),
                ("when", G(("event", "click"), ("selectionType", "button"), ("button", "@cancel"))),
                Comp("action", "native-dialog-cancel",
                     ("action", "cancelDialog"),
                     ("execution", G(("sequence", 10), ("fireOnInit", False)))))


def buttons_region():
    return Comp("region", "buttons",
                ("name", "Buttons"),
                ("type", "staticContent"),
                ("layout", G(("sequence", 20), ("slot", "dialogFooter"))),
                ("appearance", G(("template", "@/buttons-container"), ("templateOptions", "#DEFAULT#"))),
                ("settings", G(("outputAs", "text"))))


def form_page(num, name, alias, group, region_id, table, pk, pk_dtype, items, ops=("add", "update", "delete"),
              auth=None, save_cond=None, delete_cond=None, submit_doc=None, submit_cond=None,
              extra_processes=(), extra_validations=()):
    pk_item = "P%d_%s" % (num, pk)
    comps = [buttons_region()]
    comps.append(Comp("region", region_id,
                      ("name", name),
                      ("type", "form"),
                      ("source", G(("location", "localDatabase"), ("tableName", table))),
                      ("layout", G(("sequence", 10), ("slot", "contentBody"))),
                      ("appearance", G(("template", "@/blank-with-attributes"), ("templateOptions", "#DEFAULT#"))),
                      ("edit", G(("enabled", True), ("allowedOperations", A(ops))))))
    pk_spec = item(num, pk, pk, "hidden", dtype=pk_dtype)
    pk_spec["pk"] = True
    comps.append(form_item(pk_spec, region_id, 5))
    for i, spec in enumerate(items):
        comps.append(form_item(spec, region_id, (i + 1) * 10))

    def joined(base, extra):
        return base if not extra else "%s and %s" % (base, extra)

    requests = []
    comps.append(dialog_button("cancel", "CANCEL", "Cancel", 10, "close"))
    if "delete" in ops:
        comps.append(dialog_button("delete", "DELETE", "Delete", 20, "delete", db_action="delete",
                                   cond=joined(":%s is not null" % pk_item, delete_cond), danger=True,
                                   confirm="&APP_TEXT$DELETE_MSG!RAW.", validations=False))
        requests.append("DELETE")
    if "update" in ops:
        comps.append(dialog_button("save", "SAVE", "Apply Changes", 30, "next", hot=True, db_action="update",
                                   cond=joined(":%s is not null" % pk_item, save_cond)))
        requests.append("SAVE")
    if "add" in ops:
        comps.append(dialog_button("create", "CREATE", "Create", 40, "next", hot=True, db_action="insert",
                                   cond=":%s is null" % pk_item))
        requests.append("CREATE")
    if submit_doc:
        comps.append(dialog_button("submit", "SUBMIT", "Submit for Approval", 50, "next", hot=True,
                                   db_action="update",
                                   cond=joined(":%s is not null" % pk_item, submit_cond),
                                   confirm="Ajukan dokumen ini untuk approval? Setelah diajukan dokumen terkunci."))
        requests.append("SUBMIT")
    comps.append(cancel_da())
    for v in extra_validations:
        comps.append(v)
    comps.append(Comp("process", "initialize-form",
                      ("name", "Initialize form " + name),
                      ("type", "formInitialization"),
                      ("formRegion", "@" + region_id),
                      ("execution", G(("sequence", 10), ("point", "beforeHeader")))))
    comps.append(Comp("process", "process-form",
                      ("name", "Process form " + name),
                      ("type", "formAutoRowProcessing"),
                      ("formRegion", "@" + region_id),
                      ("execution", G(("sequence", 10)))))
    if submit_doc:
        comps.append(Comp("process", "submit-for-approval",
                          ("name", "Submit for Approval"),
                          ("type", "executeCode"),
                          ("source", G(("plsqlCode", ML("plsql", "mbms_approval.submit(p_doc_type => '%s', p_doc_id => :%s);"
                                                        % (submit_doc, pk_item))))),
                          ("execution", G(("sequence", 20))),
                          ("successMessage", G(("successMessage", "Dokumen diajukan untuk approval."))),
                          ("serverSideCondition", G(("whenButtonPressed", "@submit")))))
    for pr in extra_processes:
        comps.append(pr)
    comps.append(Comp("process", "close-dialog",
                      ("name", "Close Dialog"),
                      ("type", "closeDialog"),
                      ("settings", G(("showSuccessMessages", True))),
                      ("execution", G(("sequence", 50))),
                      ("serverSideCondition", G(("type", "requestIsContainedInValue"),
                                                ("value", ",".join(requests))))))
    page_members = [
        ("name", name),
        ("alias", alias),
        ("title", name),
        ("pageGroup", "@" + group) if group else None,
        ("appearance", G(("pageMode", "modalDialog"), ("dialogTemplate", "@/modal-dialog"),
                         ("templateOptions", "#DEFAULT#"))),
        ("dialog", G(("chained", False), ("resizable", True))),
        ("security", G(("authorizationScheme", "@" + auth))) if auth else None,
    ] + comps
    return Comp("page", str(num), *page_members)


def pagefile(num, alias, comp):
    put("pages/p%05d-%s.apx" % (num, alias.lower().replace("_", "-")), render(comp))


# =============================================================================
# Shared components
# =============================================================================
def sql_lov(ident, name, sql):
    return Comp("lov", ident,
                ("name", name),
                ("source", G(("type", "sqlQuery"), ("sqlQuery", ML("sql", sql)))),
                ("columnMapping", G(("return", "R"), ("display", "D"))))


def static_lov(ident, name, values):
    entries = []
    for i, (ret, disp) in enumerate(values):
        entries.append(Comp("entry", ret.lower().replace("_", "-"),
                            ("sequence", (i + 1) * 10), ("display", disp), ("return", ret)))
    return Comp("lov", ident, ("name", name), ("source", G(("location", "staticValues"))), *entries)


LOVS = [
    sql_lov("business-units", "MDM_BUSINESS_UNIT", """
select bu_code || ' - ' || bu_name d, bu_id r
  from mdm_business_unit
 where active_yn = 'Y'
 order by bu_code"""),
    sql_lov("customers", "MDM_CUSTOMER", """
select customer_code || ' - ' || customer_name d, customer_id r
  from mdm_customer
 where active_yn = 'Y'
 order by customer_name"""),
    sql_lov("items", "MDM_ITEM", """
select item_code || ' - ' || item_name || ' (' || uom || ')' d, item_id r
  from mdm_item
 where active_yn = 'Y'
 order by item_code"""),
    sql_lov("warehouses", "MDM_WAREHOUSE", """
select w.wh_code || ' - ' || w.wh_name d, w.warehouse_id r
  from mdm_warehouse w
 where w.active_yn = 'Y'
 order by w.wh_code"""),
    sql_lov("open-jobs", "PRT_JOB_ORDER (approved)", """
select job_no || ' - ' || substr(product_desc, 1, 60) d, job_id r
  from prt_job_order
 where status in ('APPROVED','IN_PROGRESS','COMPLETED')
 order by job_no desc"""),
    sql_lov("open-projects", "PRJ_PROJECT (approved)", """
select project_no || ' - ' || project_name d, project_id r
  from prj_project
 where status in ('APPROVED','IN_PROGRESS','COMPLETED')
 order by project_no desc"""),
    sql_lov("draft-projects", "PRJ_PROJECT (draft)", """
select project_no || ' - ' || project_name d, project_id r
  from prj_project
 where status in ('DRAFT','REJECTED')
 order by project_no desc"""),
    sql_lov("editable-prs", "PUR_REQUISITION (draft)", """
select pr_no || ' - ' || substr(description, 1, 60) d, pr_id r
  from pur_requisition
 where status in ('DRAFT','REJECTED')
 order by pr_no desc"""),
    sql_lov("roles", "SYS_ROLE", """
select role_code || ' - ' || role_name d, role_code r
  from sys_role
 order by role_code"""),
    static_lov("doc-status", "DOC_STATUS", [
        ("DRAFT", "Draft"), ("SUBMITTED", "Submitted"), ("APPROVED", "Approved"), ("REJECTED", "Rejected"),
        ("IN_PROGRESS", "In Progress"), ("COMPLETED", "Completed"), ("CLOSED", "Closed"), ("CANCELLED", "Cancelled")]),
    static_lov("job-types", "JOB_TYPE", [("MTO", "Make to Order (Sales Order)"), ("STOCK", "Produksi untuk Stok")]),
    static_lov("project-types", "PROJECT_TYPE", [("FABRICATION", "Fabrikasi"), ("INSTALLATION", "Instalasi"),
                                                 ("MAINTENANCE", "Maintenance Service")]),
    static_lov("item-categories", "ITEM_CATEGORY", [("RAW", "Raw Material"), ("CONSUMABLE", "Consumables"),
                                                    ("SPARE_PART", "Spare Part"), ("FINISHED_GOOD", "Finished Goods"),
                                                    ("PLATE", "Plat Cetak (repeat order)"), ("SERVICE", "Jasa")]),
    static_lov("vendor-types", "VENDOR_TYPE", [("GOODS", "Barang"), ("SUBCON", "Subkontraktor"), ("SERVICE", "Jasa")]),
    static_lov("location-types", "LOCATION_TYPE", [("MAIN", "Gudang Utama"), ("SITE", "Site Proyek"),
                                                   ("VENDOR", "Lokasi Vendor Subkon")]),
    static_lov("txn-types", "TXN_TYPE", [("RECEIPT", "Goods Receipt (masuk)"), ("ISSUE", "Material Issue ke Job/Proyek"),
                                         ("RETURN", "Material Return dari Job/Proyek"), ("ADJ_IN", "Adjustment (+)"),
                                         ("ADJ_OUT", "Adjustment (-)")]),
    static_lov("pr-purposes", "PR_PURPOSE", [("STOCK", "Stock Replenishment"), ("JOB", "Printing Job Order"),
                                             ("PROJECT", "Engineering Project")]),
    static_lov("cost-categories", "COST_CATEGORY", [("MATERIAL", "Material"), ("LABOR", "Labor"),
                                                    ("EQUIPMENT", "Equipment"), ("SUBCON", "Subkon"),
                                                    ("OPERATIONAL", "Operational"), ("OTHER", "Other")]),
    static_lov("yes-no", "YES_NO", [("Y", "Ya"), ("N", "Tidak")]),
]

# Navigation: (id, label, icon, page or None, parent, auth)
NAV = [
    ("home", "Dashboard", "fa-dashboard", 1, None, None),
    ("approvals", "Approval Inbox", "fa-check-square-o", 60, None, None),
    ("printing", "Printing", "fa-print", None, None, None),
    ("job-orders", "Job Orders", "fa-file-text-o", 20, "printing", None),
    ("job-costing", "Job Costing (HPP)", "fa-calculator", 22, "printing", None),
    ("engineering", "Engineering", "fa-wrench", None, None, None),
    ("projects", "Projects", "fa-briefcase", 30, "engineering", None),
    ("wbs-budget", "WBS & Budget vs Actual", "fa-sitemap", 32, "engineering", None),
    ("project-summary", "Project Summary", "fa-line-chart", 34, "engineering", None),
    ("procurement", "Procurement", "fa-shopping-cart", None, None, None),
    ("purchase-requisitions", "Purchase Requisitions", "fa-file-o", 40, "procurement", None),
    ("pr-lines", "PR Lines", "fa-list", 42, "procurement", None),
    ("inventory", "Inventory", "fa-cubes", None, None, None),
    ("stock-transactions", "Stock Transactions", "fa-exchange", 50, "inventory", None),
    ("stock-on-hand", "Stock On Hand", "fa-database", 52, "inventory", None),
    ("master-data", "Master Data", "fa-table", None, None, None),
    ("business-units", "Business Units", "fa-building-o", 10, "master-data", None),
    ("customers", "Customers", "fa-users", 12, "master-data", None),
    ("vendors", "Vendors", "fa-truck", 14, "master-data", None),
    ("items", "Items", "fa-tag", 16, "master-data", None),
    ("warehouses", "Warehouses & Locations", "fa-home", 18, "master-data", None),
    ("administration", "Administration", "fa-gear", None, None, "admin-rights"),
    ("users-roles", "Users & Roles", "fa-user-secret", 90, "administration", "admin-rights"),
    ("doc-types", "Document Types & Approval", "fa-sliders", 92, "administration", "admin-rights"),
]


def nav_menu():
    entries = []
    for i, (ident, label, icon, page, parent, auth) in enumerate(NAV):
        m = [("label", label), ("icon", G(("imageIconCssClasses", icon))),
             ("layout", G(("sequence", (i + 1) * 10), ("parentEntry", "@" + parent) if parent else None))]
        if page:
            m.append(("link", G(("target", O(("page", page))))))
        if auth:
            m.append(("security", G(("authorizationScheme", "@" + auth))))
        entries.append(Comp("entry", ident, *m))
    return Comp("list", "navigation-menu", ("name", "Navigation Menu"), *entries)


def nav_bar():
    return Comp("list", "navigation-bar", ("name", "Navigation Bar"),
                Comp("entry", "---",
                     ("label", "---"),
                     ("layout", G(("sequence", 20), ("parentEntry", "@app-user"))),
                     ("link", G(("target", O(("type", "url"), ("url", "separator"))))),
                     ("serverSideCondition", G(("type", "userIsAuthenticated")))),
                Comp("entry", "app-user",
                     ("label", "&APP_USER."),
                     ("icon", G(("imageIconCssClasses", "fa-user"))),
                     ("layout", G(("sequence", 10))),
                     ("link", G(("target", O(("type", "url"), ("url", "#"))))),
                     ("userDefinedAttributes", G(("2", "has-username")))),
                Comp("entry", "sign-out",
                     ("label", "Sign Out"),
                     ("icon", G(("imageIconCssClasses", "fa-sign-out"))),
                     ("layout", G(("sequence", 30), ("parentEntry", "@app-user"))),
                     ("link", G(("target", O(("type", "url"), ("url", "&LOGOUT_URL."))))),
                     ("serverSideCondition", G(("type", "userIsAuthenticated")))))


def breadcrumbs():
    entries = [Comp("entry", "home", ("name", "Home"), ("pageNumber", 1),
                    ("execution", G(("sequence", 10))), ("link", G(("target", O(("page", 1))))))]
    seq = 20
    for ident, label, _icon, page, _parent, _auth in NAV:
        if page and page != 1:
            entries.append(Comp("entry", ident, ("name", label), ("pageNumber", page),
                                ("execution", G(("sequence", seq))),
                                ("appearance", G(("parentEntry", "@home"))),
                                ("link", G(("target", O(("page", page)))))))
            seq += 10
    return Comp("breadcrumb", "breadcrumb", ("name", "Breadcrumb"), *entries)


def authorizations():
    def role_auth(ident, name, roles, msg):
        expr = " or ".join("mbms_sec.has_role('%s')" % r for r in roles)
        return Comp("authorization", ident,
                    ("name", name),
                    ("type", "plSqlFunctionBody"),
                    ("settings", G(("plsqlFunctionBody", "return %s;" % expr))),
                    ("error", G(("errorMessage", msg))))
    return [
        role_auth("admin-rights", "Admin Rights", ["ADMIN"], "Akses ditolak: hanya untuk role ADMIN."),
        role_auth("master-data-rights", "Master Data Rights", ["ADMIN", "FINANCE", "PROCUREMENT", "SALES"],
                  "Akses ditolak: perubahan master data hanya untuk ADMIN/FINANCE/PROCUREMENT/SALES."),
        role_auth("printing-rights", "Printing Rights", ["PRINT_MGR", "SALES", "DIRECTOR"],
                  "Akses ditolak: hanya untuk Printing Manager/Sales/Director."),
        role_auth("engineering-rights", "Engineering Rights", ["PROJECT_MGR", "ENG_MGR", "DIRECTOR"],
                  "Akses ditolak: hanya untuk Project Manager/Engineering Manager/Director."),
        role_auth("warehouse-rights", "Warehouse Rights", ["WAREHOUSE"],
                  "Akses ditolak: transaksi stok hanya untuk role WAREHOUSE."),
    ]


# =============================================================================
# Application-level files
# =============================================================================
def application():
    return Comp("app", "MBMS",
                ("name", "MBMS - PT. Multisarana Niaga Mandiri"),
                ("logo", G(("type", "text"), ("text", "MBMS"))),
                ("navigation", G(("homeUrl", O(("page", 1))), ("loginUrl", O(("page", "LOGIN"))))),
                ("navigationMenu", G(("listTemplate", "@/side-navigation-menu"),
                                     ("templateOptions", A(["#DEFAULT#", "js-defaultCollapsed", "js-navCollapsed--hidden",
                                                            "t-TreeNav--styleA"])),
                                     ("list", "@navigation-menu"))),
                ("navigationBar", G(("list", "@navigation-bar"), ("listTemplate", "@/navigation-bar"),
                                    ("templateOptions", "#DEFAULT#"))),
                ("userInterface", G(("currentTheme", "@universal-theme"), ("globalPage", 0),
                                    ("addBuiltWithApexToFooter", False))),
                ("appFormatMasks", G(("date", "DD-MON-YYYY"), ("timestamp", "DS"), ("timestampTimeZone", "DS"))),
                ("authentication", G(("scheme", "@oracle-apex-accounts"))),
                ("sessionStateProtection", G(("checksumSalt",
                                              "6D4B2F0A9C1E47B8A3D5F7091C2E4B6D8F0A1C3E5B7D9F1A3C5E7B9D1F3A5C7E"))),
                ("runtime", G(("allowFeedback", False), ("compatibilityMode", "24.2"))))


def page_groups():
    groups = [("master-data", "Master Data"), ("printing", "Printing"), ("engineering", "Engineering"),
              ("procurement", "Procurement"), ("inventory", "Inventory"), ("approval", "Approval"),
              ("administration", "Administration")]
    return render(*[Comp("pageGroup", g, ("name", n)) for g, n in groups])


# =============================================================================
# Pages
# =============================================================================
STATUS_HELP = "Status hanya berubah lewat Submit for Approval / Approval Inbox."


def pages():
    # ---------------------------------------------------------------- Home
    kpi_sql = """
select (select count(*) from sys_approval_v where status = 'PENDING' and can_act_yn = 'Y') pending_for_me
     , (select count(*) from prt_job_order where status in ('APPROVED','IN_PROGRESS')) active_jobs
     , (select count(*) from prj_project where status in ('APPROVED','IN_PROGRESS')) active_projects
     , (select count(*) from pur_requisition where status = 'SUBMITTED') open_prs
     , (select count(*) from inv_stock_on_hand_v where below_min_yn = 'Y') items_below_min
  from dual"""
    kpi_cols = [("PENDING_FOR_ME", "Approval Menunggu Anda"), ("ACTIVE_JOBS", "Job Order Aktif"),
                ("ACTIVE_PROJECTS", "Proyek Aktif"), ("OPEN_PRS", "PR Menunggu Approval"),
                ("ITEMS_BELOW_MIN", "Item di Bawah Min. Stok")]
    kpi = Comp("region", "kpi",
               ("name", "Ringkasan"),
               ("type", "classicReport"),
               ("source", G(("location", "localDatabase"), ("type", "sqlQuery"), ("sqlQuery", ML("sql", kpi_sql)))),
               ("layout", G(("sequence", 10), ("slot", "body"))),
               ("appearance", G(("template", "@/standard"), ("templateOptions", "#DEFAULT#"))),
               ("componentAppearance", G(("template", "@/standard"),
                                         ("templateOptions", A(["#DEFAULT#", "t-Report--stretch", "t-Report--hideNoPagination"])))),
               *[Comp("column", c, ("reportColumnQueryId", i + 1), ("derivedColumn", "N"),
                      ("heading", G(("heading", h), ("alignment", "center"))),
                      ("layout", G(("sequence", i + 1), ("columnAlignment", "center"))))
                 for i, (c, h) in enumerate(kpi_cols)])

    def chart(ident, name, ctype, seq, series, new_row=True, legend=False):
        ser = []
        for i, (sid, sname, sql, label, value) in enumerate(series):
            ser.append(Comp("series", sid,
                            ("name", sname),
                            ("execution", G(("sequence", (i + 1) * 10))),
                            ("source", G(("type", "sqlQuery"), ("sqlQuery", ML("sql", sql)))),
                            ("columnMapping", G(("label", label), ("value", value))),
                            ("label", G(("show", ctype == "pie"))),
                            ("performance", G(("maxRowsToProcess", 50)))))
        return Comp("region", ident,
                    ("name", name),
                    ("type", "chart"),
                    ("layout", G(("sequence", seq), ("slot", "body"), ("startNewRow", False) if not new_row else None)),
                    ("appearance", G(("template", "@/standard"), ("templateOptions", A(["#DEFAULT#", "t-Region--scrollBody"])))),
                    ("chart", G(("type", ctype))),
                    ("performance", G(("lazyLoading", True))),
                    ("value", G(("format", "decimal"), ("decimalPlaces", 0))),
                    ("legend", G(("show", legend))),
                    *ser)

    home = Comp("page", "1",
                ("name", "Dashboard"),
                ("alias", "HOME"),
                ("title", "Dashboard"),
                ("appearance", G(("pageTemplate", "@/standard"), ("templateOptions", "#DEFAULT#"))),
                ("navigation", G(("cursorFocus", "doNotFocusCursor"))),
                ("security", G(("pageAccessProtection", "argumentsMustHaveChecksum"), ("formAutoComplete", False))),
                Comp("region", "app-name",
                     ("name", "Home"),
                     ("title", "MBMS Dashboard"),
                     ("type", "staticContent"),
                     ("source", G(("htmlCode", "Satu sistem untuk Printing (Job Manufacturing) dan Engineering (Project Cost Control) di atas shared core. MVP sandbox - data dummy."))),
                     ("layout", G(("sequence", 10), ("slot", "breadcrumbBar"))),
                     ("appearance", G(("template", "@/hero"), ("templateOptions", "#DEFAULT#"))),
                     ("image", G(("fileUrl", "#APP_FILES#icons/app-icon-512.png")))),
                kpi,
                chart("job-status", "Job Order per Status", "pie", 20, [
                    ("series", "Job Orders", "select status, count(*) value from prt_job_order group by status order by 2 desc",
                     "STATUS", "VALUE")]),
                chart("stock-value", "Nilai Stok per Gudang", "bar", 30, [
                    ("series", "Nilai Stok", "select wh_code, sum(stock_value) value from inv_stock_on_hand_v group by wh_code order by 1",
                     "WH_CODE", "VALUE")], new_row=False),
                chart("project-budget", "Proyek: Budget vs Aktual", "bar", 40, [
                    ("budget", "Budget", "select project_no, budget_amount from prj_project_summary_v order by project_no",
                     "PROJECT_NO", "BUDGET_AMOUNT"),
                    ("actual", "Aktual", "select project_no, actual_amount from prj_project_summary_v order by project_no",
                     "PROJECT_NO", "ACTUAL_AMOUNT")], legend=True),
                chart("job-hpp", "Job: HPP Estimasi vs Aktual", "bar", 50, [
                    ("estimated", "Estimasi", "select job_no, est_hpp from prt_job_cost_v where status <> 'DRAFT' order by job_no",
                     "JOB_NO", "EST_HPP"),
                    ("actual", "Aktual", "select job_no, act_hpp from prt_job_cost_v where status <> 'DRAFT' order by job_no",
                     "JOB_NO", "ACT_HPP")], new_row=False, legend=True))
    pagefile(1, "home", home)

    # ---------------------------------------------------------------- Master data
    pagefile(10, "business-units", ir_page(10, "Business Units", "BUSINESS-UNITS", "master-data", "business-units", """
select bu_id, bu_code, bu_name, active_yn, updated_by, updated_on
  from mdm_business_unit""",
        [("BU_ID", "ID", "hidden"), ("BU_CODE", "Kode", "text"), ("BU_NAME", "Nama", "text"),
         ("ACTIVE_YN", "Aktif", "text"), ("UPDATED_BY", "Diubah Oleh", "text"), ("UPDATED_ON", "Diubah", "date")],
        form_page=11, pk="BU_ID", sort_col="BU_CODE", create_auth="admin-rights"))
    pagefile(11, "business-unit", form_page(11, "Business Unit", "BUSINESS-UNIT", "master-data", "business-unit",
        "MDM_BUSINESS_UNIT", "BU_ID", "number", [
            item(11, "BU_CODE", "Kode BU", req=True, maxlen=10),
            item(11, "BU_NAME", "Nama BU", req=True, maxlen=100),
            item(11, "ACTIVE_YN", "Aktif", "select", req=True, lov="@yes-no", default_static="Y"),
        ], auth="admin-rights"))

    pagefile(12, "customers", ir_page(12, "Customers", "CUSTOMERS", "master-data", "customers", """
select customer_id, customer_code, customer_name, npwp, nitku, city, contact_person, phone, email,
       payment_term_days, active_yn
  from mdm_customer""",
        [("CUSTOMER_ID", "ID", "hidden"), ("CUSTOMER_CODE", "Kode", "text"), ("CUSTOMER_NAME", "Nama Customer", "text"),
         ("NPWP", "NPWP", "text"), ("NITKU", "NITKU", "text"), ("CITY", "Kota", "text"),
         ("CONTACT_PERSON", "Contact Person", "text"), ("PHONE", "Telepon", "text"), ("EMAIL", "Email", "text"),
         ("PAYMENT_TERM_DAYS", "TOP (hari)", "num"), ("ACTIVE_YN", "Aktif", "text")],
        form_page=13, pk="CUSTOMER_ID", sort_col="CUSTOMER_NAME", create_auth="master-data-rights"))
    pagefile(13, "customer", form_page(13, "Customer", "CUSTOMER", "master-data", "customer", "MDM_CUSTOMER",
        "CUSTOMER_ID", "number", [
            item(13, "CUSTOMER_CODE", "Kode Customer", req=True, maxlen=30),
            item(13, "CUSTOMER_NAME", "Nama Customer", req=True, maxlen=200),
            item(13, "NPWP", "NPWP", maxlen=30),
            item(13, "NITKU", "NITKU", maxlen=30),
            item(13, "ADDRESS", "Alamat", "textarea", maxlen=500),
            item(13, "CITY", "Kota", maxlen=100),
            item(13, "CONTACT_PERSON", "Contact Person", maxlen=100),
            item(13, "PHONE", "Telepon", maxlen=50),
            item(13, "EMAIL", "Email", maxlen=200),
            item(13, "PAYMENT_TERM_DAYS", "Payment Term (hari)", "number", req=True, dtype="number", default_static="30", min_value=0),
            item(13, "ACTIVE_YN", "Aktif", "select", req=True, lov="@yes-no", default_static="Y"),
        ], auth="master-data-rights"))

    pagefile(14, "vendors", ir_page(14, "Vendors", "VENDORS", "master-data", "vendors", """
select vendor_id, vendor_code, vendor_name, vendor_type, npwp, city, contact_person, phone, email,
       payment_term_days, active_yn
  from mdm_vendor""",
        [("VENDOR_ID", "ID", "hidden"), ("VENDOR_CODE", "Kode", "text"), ("VENDOR_NAME", "Nama Vendor", "text"),
         ("VENDOR_TYPE", "Tipe", "text"), ("NPWP", "NPWP", "text"), ("CITY", "Kota", "text"),
         ("CONTACT_PERSON", "Contact Person", "text"), ("PHONE", "Telepon", "text"), ("EMAIL", "Email", "text"),
         ("PAYMENT_TERM_DAYS", "TOP (hari)", "num"), ("ACTIVE_YN", "Aktif", "text")],
        form_page=15, pk="VENDOR_ID", sort_col="VENDOR_NAME", create_auth="master-data-rights"))
    pagefile(15, "vendor", form_page(15, "Vendor", "VENDOR", "master-data", "vendor", "MDM_VENDOR",
        "VENDOR_ID", "number", [
            item(15, "VENDOR_CODE", "Kode Vendor", req=True, maxlen=30),
            item(15, "VENDOR_NAME", "Nama Vendor", req=True, maxlen=200),
            item(15, "VENDOR_TYPE", "Tipe Vendor", "select", req=True, lov="@vendor-types", default_static="GOODS"),
            item(15, "NPWP", "NPWP", maxlen=30),
            item(15, "ADDRESS", "Alamat", "textarea", maxlen=500),
            item(15, "CITY", "Kota", maxlen=100),
            item(15, "CONTACT_PERSON", "Contact Person", maxlen=100),
            item(15, "PHONE", "Telepon", maxlen=50),
            item(15, "EMAIL", "Email", maxlen=200),
            item(15, "PAYMENT_TERM_DAYS", "Payment Term (hari)", "number", req=True, dtype="number", default_static="30", min_value=0),
            item(15, "ACTIVE_YN", "Aktif", "select", req=True, lov="@yes-no", default_static="Y"),
        ], auth="master-data-rights"))

    pagefile(16, "items", ir_page(16, "Items", "ITEMS", "master-data", "items", """
select i.item_id, i.item_code, i.item_name, i.item_category, i.uom, bu.bu_code, i.min_stock, i.std_cost, i.active_yn
  from mdm_item i
  left join mdm_business_unit bu on bu.bu_id = i.bu_id""",
        [("ITEM_ID", "ID", "hidden"), ("ITEM_CODE", "Kode", "text"), ("ITEM_NAME", "Nama Item", "text"),
         ("ITEM_CATEGORY", "Kategori", "text"), ("UOM", "UoM", "text"), ("BU_CODE", "BU", "text"),
         ("MIN_STOCK", "Min. Stok", "qty"), ("STD_COST", "Std Cost", "money"), ("ACTIVE_YN", "Aktif", "text")],
        form_page=17, pk="ITEM_ID", sort_col="ITEM_CODE", create_auth="master-data-rights"))
    pagefile(17, "item", form_page(17, "Item", "ITEM", "master-data", "item", "MDM_ITEM", "ITEM_ID", "number", [
        item(17, "ITEM_CODE", "Kode Item", req=True, maxlen=30),
        item(17, "ITEM_NAME", "Nama Item", req=True, maxlen=200),
        item(17, "ITEM_CATEGORY", "Kategori", "select", req=True, lov="@item-categories"),
        item(17, "UOM", "Satuan (UoM)", req=True, maxlen=20),
        item(17, "BU_ID", "Business Unit", "select", dtype="number", lov="@business-units", null_text="- Shared -"),
        item(17, "MIN_STOCK", "Minimum Stok / Reorder Point", "number", req=True, dtype="number", default_static="0", min_value=0),
        item(17, "STD_COST", "Standard Cost", "number", req=True, dtype="number", default_static="0", min_value=0),
        item(17, "ACTIVE_YN", "Aktif", "select", req=True, lov="@yes-no", default_static="Y"),
    ], auth="master-data-rights"))

    pagefile(18, "warehouses", ir_page(18, "Warehouses & Locations", "WAREHOUSES", "master-data", "warehouses", """
select w.warehouse_id, w.wh_code, w.wh_name, bu.bu_code, w.location_type, w.active_yn
  from mdm_warehouse w
  join mdm_business_unit bu on bu.bu_id = w.bu_id""",
        [("WAREHOUSE_ID", "ID", "hidden"), ("WH_CODE", "Kode", "text"), ("WH_NAME", "Nama", "text"),
         ("BU_CODE", "BU", "text"), ("LOCATION_TYPE", "Tipe Lokasi", "text"), ("ACTIVE_YN", "Aktif", "text")],
        form_page=19, pk="WAREHOUSE_ID", sort_col="WH_CODE", create_auth="master-data-rights"))
    pagefile(19, "warehouse", form_page(19, "Warehouse / Location", "WAREHOUSE", "master-data", "warehouse",
        "MDM_WAREHOUSE", "WAREHOUSE_ID", "number", [
            item(19, "WH_CODE", "Kode Gudang/Lokasi", req=True, maxlen=30),
            item(19, "WH_NAME", "Nama", req=True, maxlen=200),
            item(19, "BU_ID", "Business Unit (pemilik)", "select", req=True, dtype="number", lov="@business-units"),
            item(19, "LOCATION_TYPE", "Tipe Lokasi", "select", req=True, lov="@location-types", default_static="MAIN",
                 help="Site proyek dan vendor subkon dicatat sebagai lokasi di bawah gudang BU pemilik (D-04, BR-12)."),
            item(19, "ACTIVE_YN", "Aktif", "select", req=True, lov="@yes-no", default_static="Y"),
        ], auth="master-data-rights"))

    # ---------------------------------------------------------------- Printing
    pagefile(20, "job-orders", ir_page(20, "Job Orders", "JOB-ORDERS", "printing", "job-orders", """
select j.job_id, j.job_no, j.job_type, c.customer_name, j.product_desc, j.qty_order, j.ups_per_sheet,
       j.due_date, j.selling_price, j.est_hpp, j.status, j.created_by
  from prt_job_order j
  left join mdm_customer c on c.customer_id = j.customer_id""",
        [("JOB_ID", "ID", "hidden"), ("JOB_NO", "No. Job", "text"), ("JOB_TYPE", "Tipe", "text"),
         ("CUSTOMER_NAME", "Customer", "text"), ("PRODUCT_DESC", "Produk / Spesifikasi", "text"),
         ("QTY_ORDER", "Qty", "qty"), ("UPS_PER_SHEET", "Up/Lembar", "num"), ("DUE_DATE", "Due Date", "date"),
         ("SELLING_PRICE", "Harga Jual", "money"), ("EST_HPP", "Est. HPP", "money"), ("STATUS", "Status", "text"),
         ("CREATED_BY", "Dibuat Oleh", "text")],
        form_page=21, pk="JOB_ID", sort_col="JOB_NO", sort_desc=True, create_auth="printing-rights"))
    jo_ops = "nvl(:P21_STATUS,'DRAFT') in ('DRAFT','REJECTED')"
    pagefile(21, "job-order", form_page(21, "Job Order", "JOB-ORDER", "printing", "job-order", "PRT_JOB_ORDER",
        "JOB_ID", "number", [
            item(21, "JOB_NO", "No. Job Order", "display", query_only=True),
            item(21, "STATUS", "Status", "select", lov="@doc-status", default_static="DRAFT",
                 readonly_expr="nvl(:P21_STATUS,'DRAFT') not in ('APPROVED','IN_PROGRESS','COMPLETED')",
                 help="Setelah approved: ubah ke IN_PROGRESS / COMPLETED / CLOSED. " + STATUS_HELP),
            item(21, "BU_ID", "BU", "hidden", dtype="number",
                 default_sql="select bu_id from mdm_business_unit where bu_code = 'PRT'"),
            item(21, "JOB_TYPE", "Tipe Produksi (D-02)", "select", req=True, lov="@job-types", default_static="MTO",
                 readonly_expr="not (" + jo_ops + ")"),
            item(21, "CUSTOMER_ID", "Customer", "select", dtype="number", lov="@customers",
                 readonly_expr="not (" + jo_ops + ")", help="Wajib untuk Make to Order."),
            item(21, "PRODUCT_DESC", "Produk / Spesifikasi", "textarea", req=True, maxlen=500,
                 readonly_expr="not (" + jo_ops + ")"),
            item(21, "QTY_ORDER", "Qty Order", "number", req=True, dtype="number", min_value=1,
                 readonly_expr="not (" + jo_ops + ")"),
            item(21, "UPS_PER_SHEET", "Imposition (up per lembar)", "number", req=True, dtype="number",
                 default_static="1", min_value=1, readonly_expr="not (" + jo_ops + ")"),
            item(21, "INSHEET_PCT", "Toleransi Insheet (%)", "number", req=True, dtype="number", default_static="5",
                 min_value=0, max_value=100, readonly_expr="not (" + jo_ops + ")"),
            item(21, "DUE_DATE", "Due Date", "date", dtype="date"),
            item(21, "SELLING_PRICE", "Harga Jual", "number", req=True, dtype="number", default_static="0",
                 min_value=0, readonly_expr="not (" + jo_ops + ")"),
            item(21, "EST_PAPER", "Est. Kertas", "number", dtype="number", default_static="0", min_value=0,
                 readonly_expr="not (" + jo_ops + ")"),
            item(21, "EST_INK", "Est. Tinta", "number", dtype="number", default_static="0", min_value=0,
                 readonly_expr="not (" + jo_ops + ")"),
            item(21, "EST_PLATE", "Est. Plat", "number", dtype="number", default_static="0", min_value=0,
                 readonly_expr="not (" + jo_ops + ")"),
            item(21, "EST_MACHINE", "Est. Proses Mesin", "number", dtype="number", default_static="0", min_value=0,
                 readonly_expr="not (" + jo_ops + ")"),
            item(21, "EST_FINISHING", "Est. Finishing (internal/subkon)", "number", dtype="number", default_static="0",
                 min_value=0, readonly_expr="not (" + jo_ops + ")"),
            item(21, "EST_LABOR", "Est. Tenaga Kerja", "number", dtype="number", default_static="0", min_value=0,
                 readonly_expr="not (" + jo_ops + ")"),
            item(21, "EST_OVERHEAD", "Est. Overhead", "number", dtype="number", default_static="0", min_value=0,
                 readonly_expr="not (" + jo_ops + ")"),
            item(21, "EST_HPP", "Total Est. HPP", "display", dtype="number", query_only=True),
            item(21, "QTY_PRODUCED", "Qty Produced", "number", dtype="number", default_static="0", min_value=0),
            item(21, "QTY_REJECT", "Qty Reject / Waste", "number", dtype="number", default_static="0", min_value=0),
            item(21, "QTY_DELIVERED", "Qty Delivered", "number", dtype="number", default_static="0", min_value=0),
            item(21, "ACT_OTHER_COST", "Biaya Aktual Lain (mesin, labor, subkon, overhead)", "number", dtype="number",
                 default_static="0", min_value=0,
                 help="Material aktual dihitung otomatis dari Material Issue. Detail labor/mesin/subkon menyusul di Fase 2."),
            item(21, "NOTES", "Catatan", "textarea", maxlen=1000),
        ], auth="printing-rights",
        save_cond="nvl(:P21_STATUS,'DRAFT') not in ('SUBMITTED','CLOSED','CANCELLED')",
        delete_cond="nvl(:P21_STATUS,'DRAFT') = 'DRAFT'",
        submit_doc="JO", submit_cond=jo_ops,
        extra_validations=[val_expr("customer-required-for-mto", "Customer wajib untuk MTO", 10, ":P21_JOB_TYPE = 'STOCK' or :P21_CUSTOMER_ID is not null",
                     "Customer wajib diisi untuk job Make to Order.", "P21_CUSTOMER_ID", requests="CREATE,SAVE,SUBMIT")]))

    pagefile(22, "job-costing", ir_page(22, "Job Costing (HPP)", "JOB-COSTING", "printing", "job-costing", """
select job_id, job_no, job_type, customer_name, product_desc, status, due_date, qty_order, qty_produced,
       qty_reject, qty_delivered, insheet_pct, waste_pct, selling_price, est_hpp, act_material,
       act_other_cost, act_hpp, hpp_variance, est_gross_profit, act_gross_profit, act_margin_pct
  from prt_job_cost_v""",
        [("JOB_ID", "ID", "hidden"), ("JOB_NO", "No. Job", "text"), ("JOB_TYPE", "Tipe", "text"),
         ("CUSTOMER_NAME", "Customer", "text"), ("PRODUCT_DESC", "Produk", "text"), ("STATUS", "Status", "text"),
         ("DUE_DATE", "Due Date", "date"), ("QTY_ORDER", "Qty Order", "qty"), ("QTY_PRODUCED", "Produced", "qty"),
         ("QTY_REJECT", "Reject", "qty"), ("QTY_DELIVERED", "Delivered", "qty"), ("INSHEET_PCT", "Toleransi %", "pct"),
         ("WASTE_PCT", "Waste %", "pct"), ("SELLING_PRICE", "Harga Jual", "money"), ("EST_HPP", "Est. HPP", "money"),
         ("ACT_MATERIAL", "Material Aktual", "money"), ("ACT_OTHER_COST", "Biaya Lain", "money"),
         ("ACT_HPP", "HPP Aktual", "money"), ("HPP_VARIANCE", "Varians HPP", "money"),
         ("EST_GROSS_PROFIT", "Est. Gross Profit", "money"), ("ACT_GROSS_PROFIT", "Gross Profit Aktual", "money"),
         ("ACT_MARGIN_PCT", "Margin %", "pct")],
        sort_col="JOB_NO", sort_desc=True,
        help_text="Actual costing per job (D-07): HPP aktual = material yang di-issue (rata-rata biaya) + biaya aktual lain. Varians positif = penghematan."))

    # ---------------------------------------------------------------- Engineering
    pagefile(30, "projects", ir_page(30, "Projects", "PROJECTS", "engineering", "projects", """
select p.project_id, p.project_no, p.project_name, p.project_type, c.customer_name, p.contract_value,
       p.retention_pct, p.start_date, p.end_date, p.progress_pct, p.project_manager, p.status
  from prj_project p
  join mdm_customer c on c.customer_id = p.customer_id""",
        [("PROJECT_ID", "ID", "hidden"), ("PROJECT_NO", "No. Proyek", "text"), ("PROJECT_NAME", "Nama Proyek", "text"),
         ("PROJECT_TYPE", "Tipe", "text"), ("CUSTOMER_NAME", "Customer", "text"),
         ("CONTRACT_VALUE", "Nilai Kontrak", "money"), ("RETENTION_PCT", "Retensi %", "pct"),
         ("START_DATE", "Mulai", "date"), ("END_DATE", "Target Selesai", "date"), ("PROGRESS_PCT", "Progres %", "pct"),
         ("PROJECT_MANAGER", "PM", "text"), ("STATUS", "Status", "text")],
        form_page=31, pk="PROJECT_ID", sort_col="PROJECT_NO", sort_desc=True, create_auth="engineering-rights",
        column_links=[("PROJECT_NO", O(("page", 32), ("items", O(("IR_PROJECT_NO", "#PROJECT_NO#"))),
                                       ("clearCache", 32), ("action", "resetRegions")))]))
    prj_ops = "nvl(:P31_STATUS,'DRAFT') in ('DRAFT','REJECTED')"
    pagefile(31, "project", form_page(31, "Project", "PROJECT", "engineering", "project", "PRJ_PROJECT",
        "PROJECT_ID", "number", [
            item(31, "PROJECT_NO", "No. Proyek", "display", query_only=True),
            item(31, "STATUS", "Status", "select", lov="@doc-status", default_static="DRAFT",
                 readonly_expr="nvl(:P31_STATUS,'DRAFT') not in ('APPROVED','IN_PROGRESS','COMPLETED')",
                 help="Budget diajukan lewat Submit for Approval setelah WBS diisi. " + STATUS_HELP),
            item(31, "BU_ID", "BU", "hidden", dtype="number",
                 default_sql="select bu_id from mdm_business_unit where bu_code = 'ENG'"),
            item(31, "PROJECT_NAME", "Nama Proyek", req=True, maxlen=300, width=60),
            item(31, "PROJECT_TYPE", "Tipe Proyek (D-03)", "select", req=True, lov="@project-types",
                 default_static="FABRICATION"),
            item(31, "CUSTOMER_ID", "Customer", "select", req=True, dtype="number", lov="@customers",
                 readonly_expr="not (" + prj_ops + ")"),
            item(31, "CONTRACT_VALUE", "Nilai Kontrak", "number", req=True, dtype="number", default_static="0",
                 min_value=0, readonly_expr="not (" + prj_ops + ")",
                 help="Setelah approved, perubahan nilai kontrak lewat Change Order (Fase 3)."),
            item(31, "RETENTION_PCT", "Retensi (%)", "number", req=True, dtype="number", default_static="5",
                 min_value=0, max_value=100),
            item(31, "START_DATE", "Tanggal Mulai", "date", dtype="date"),
            item(31, "END_DATE", "Target Selesai", "date", dtype="date"),
            item(31, "PROGRESS_PCT", "Progres (%) - metode output (D-08)", "number", req=True, dtype="number",
                 default_static="0", min_value=0, max_value=100),
            item(31, "PROJECT_MANAGER", "Project Manager", maxlen=255),
            item(31, "NOTES", "Catatan", "textarea", maxlen=1000),
        ], auth="engineering-rights",
        save_cond="nvl(:P31_STATUS,'DRAFT') not in ('SUBMITTED','CLOSED','CANCELLED')",
        delete_cond="nvl(:P31_STATUS,'DRAFT') = 'DRAFT'",
        submit_doc="PRJ", submit_cond=prj_ops))

    pagefile(32, "wbs-budget", ir_page(32, "WBS & Budget vs Actual", "WBS-BUDGET", "engineering", "wbs-budget", """
select wbs_id, project_no, project_name, project_status, wbs_code, wbs_name, cost_category, budget_amount,
       actual_amount, committed_amount, variance_amount, remaining_amount, used_pct
  from prj_wbs_budget_v""",
        [("WBS_ID", "ID", "hidden"), ("PROJECT_NO", "No. Proyek", "text"), ("PROJECT_NAME", "Proyek", "text"),
         ("PROJECT_STATUS", "Status Proyek", "text"), ("WBS_CODE", "WBS", "text"), ("WBS_NAME", "Aktivitas", "text"),
         ("COST_CATEGORY", "Kategori Biaya", "text"), ("BUDGET_AMOUNT", "Budget", "money"),
         ("ACTUAL_AMOUNT", "Aktual", "money"), ("COMMITTED_AMOUNT", "Committed (PR)", "money"),
         ("VARIANCE_AMOUNT", "Varians", "money"), ("REMAINING_AMOUNT", "Sisa Anggaran", "money"),
         ("USED_PCT", "Terpakai %", "pct")],
        form_page=33, pk="WBS_ID", sort_col="WBS_CODE", create_auth="engineering-rights",
        help_text="Varians positif berarti penghematan. Budget WBS hanya bisa diubah saat proyek DRAFT/REJECTED."))
    pagefile(33, "wbs", form_page(33, "WBS Budget", "WBS", "engineering", "wbs", "PRJ_WBS", "WBS_ID", "number", [
        item(33, "PROJECT_ID", "Proyek (DRAFT/REJECTED)", "select", req=True, dtype="number", lov="@draft-projects"),
        item(33, "WBS_CODE", "Kode WBS", req=True, maxlen=20),
        item(33, "WBS_NAME", "Aktivitas", req=True, maxlen=200),
        item(33, "COST_CATEGORY", "Kategori Biaya", "select", req=True, lov="@cost-categories", default_static="MATERIAL"),
        item(33, "BUDGET_AMOUNT", "Budget", "number", req=True, dtype="number", default_static="0", min_value=0),
    ], auth="engineering-rights"))

    pagefile(34, "project-summary", ir_page(34, "Project Summary", "PROJECT-SUMMARY", "engineering", "project-summary", """
select project_id, project_no, project_name, project_type, customer_name, status, start_date, end_date,
       progress_pct, contract_value, retention_pct, retention_amount, budget_amount, actual_amount,
       cost_variance, planned_margin, loss_warning_yn, overdue_yn
  from prj_project_summary_v""",
        [("PROJECT_ID", "ID", "hidden"), ("PROJECT_NO", "No. Proyek", "text"), ("PROJECT_NAME", "Proyek", "text"),
         ("PROJECT_TYPE", "Tipe", "text"), ("CUSTOMER_NAME", "Customer", "text"), ("STATUS", "Status", "text"),
         ("START_DATE", "Mulai", "date"), ("END_DATE", "Target", "date"), ("PROGRESS_PCT", "Progres %", "pct"),
         ("CONTRACT_VALUE", "Nilai Kontrak", "money"), ("RETENTION_PCT", "Retensi %", "pct"),
         ("RETENTION_AMOUNT", "Nilai Retensi", "money"), ("BUDGET_AMOUNT", "Budget", "money"),
         ("ACTUAL_AMOUNT", "Aktual", "money"), ("COST_VARIANCE", "Cost Variance", "money"),
         ("PLANNED_MARGIN", "Planned Margin", "money"), ("LOSS_WARNING_YN", "Estimasi Rugi?", "text"),
         ("OVERDUE_YN", "Terlambat?", "text")],
        sort_col="PROJECT_NO", sort_desc=True,
        help_text="Peringatan: Estimasi Rugi = budget melebihi nilai kontrak (PSAK 72 onerous contract); Terlambat = melewati target selesai."))

    # ---------------------------------------------------------------- Procurement
    pagefile(40, "purchase-requisitions", ir_page(40, "Purchase Requisitions", "PURCHASE-REQUISITIONS", "procurement",
        "purchase-requisitions", """
select pr_id, pr_no, bu_code, pr_date, purpose, job_no, project_no, wbs_code, requested_by, need_date,
       description, line_count, total_amount, status
  from pur_requisition_v""",
        [("PR_ID", "ID", "hidden"), ("PR_NO", "No. PR", "text"), ("BU_CODE", "BU", "text"), ("PR_DATE", "Tanggal", "date"),
         ("PURPOSE", "Tujuan", "text"), ("JOB_NO", "Job", "text"), ("PROJECT_NO", "Proyek", "text"),
         ("WBS_CODE", "WBS", "text"), ("REQUESTED_BY", "Requester", "text"), ("NEED_DATE", "Dibutuhkan", "date"),
         ("DESCRIPTION", "Keterangan", "text"), ("LINE_COUNT", "Jml Baris", "num"),
         ("TOTAL_AMOUNT", "Total", "money"), ("STATUS", "Status", "text")],
        form_page=41, pk="PR_ID", sort_col="PR_NO", sort_desc=True,
        column_links=[("LINE_COUNT", O(("page", 42), ("items", O(("IR_PR_NO", "#PR_NO#"))),
                                       ("clearCache", 42), ("action", "resetRegions")))]))
    pr_ops = "nvl(:P41_STATUS,'DRAFT') in ('DRAFT','REJECTED')"
    pagefile(41, "purchase-requisition", form_page(41, "Purchase Requisition", "PURCHASE-REQUISITION", "procurement",
        "purchase-requisition", "PUR_REQUISITION", "PR_ID", "number", [
            item(41, "PR_NO", "No. PR", "display", query_only=True),
            item(41, "STATUS", "Status", "display", query_only=True),
            item(41, "BU_ID", "Business Unit", "select", req=True, dtype="number", lov="@business-units"),
            item(41, "PR_DATE", "Tanggal PR", "date", req=True, dtype="date", default_sql="select trunc(sysdate) from dual"),
            item(41, "PURPOSE", "Tujuan Pembelian", "select", req=True, lov="@pr-purposes", default_static="STOCK"),
            item(41, "JOB_ID", "Job Order", "select", dtype="number", lov="@open-jobs",
                 help="Wajib bila tujuan = Printing Job Order."),
            item(41, "PROJECT_ID", "Proyek", "select", dtype="number", lov="@open-projects",
                 help="Wajib bila tujuan = Engineering Project. Budget dicek saat Submit (BR-03)."),
            item(41, "WBS_ID", "WBS", "select", dtype="number", cascade="P41_PROJECT_ID",
                 lov="select wbs_code || ' - ' || wbs_name d, wbs_id r from prj_wbs where project_id = :P41_PROJECT_ID order by wbs_code"),
            item(41, "NEED_DATE", "Tanggal Dibutuhkan", "date", dtype="date"),
            item(41, "DESCRIPTION", "Keterangan", "textarea", maxlen=1000),
        ],
        save_cond=pr_ops, delete_cond=pr_ops, submit_doc="PR", submit_cond=pr_ops,
        extra_validations=[
            val_expr("job-required", "Job wajib untuk tujuan JOB", 10, ":P41_PURPOSE <> 'JOB' or :P41_JOB_ID is not null",
                     "Pilih Job Order untuk PR tujuan Printing Job Order.", "P41_JOB_ID", requests="CREATE,SAVE,SUBMIT"),
            val_expr("project-required", "Proyek wajib untuk tujuan PROJECT", 20, ":P41_PURPOSE <> 'PROJECT' or :P41_PROJECT_ID is not null",
                     "Pilih Proyek untuk PR tujuan Engineering Project.", "P41_PROJECT_ID", requests="CREATE,SAVE,SUBMIT"),
        ]))

    pagefile(42, "pr-lines", ir_page(42, "PR Lines", "PR-LINES", "procurement", "pr-lines", """
select line_id, pr_no, pr_status, line_no, item_code, item_name, uom, qty, unit_price, line_amount, notes
  from pur_requisition_line_v""",
        [("LINE_ID", "ID", "hidden"), ("PR_NO", "No. PR", "text"), ("PR_STATUS", "Status PR", "text"),
         ("LINE_NO", "Baris", "num"), ("ITEM_CODE", "Kode Item", "text"), ("ITEM_NAME", "Nama Item", "text"),
         ("UOM", "UoM", "text"), ("QTY", "Qty", "qty"), ("UNIT_PRICE", "Harga Satuan", "money"),
         ("LINE_AMOUNT", "Jumlah", "money"), ("NOTES", "Catatan", "text")],
        form_page=43, pk="LINE_ID", sort_col="PR_NO", sort_desc=True))
    pagefile(43, "pr-line", form_page(43, "PR Line", "PR-LINE", "procurement", "pr-line", "PUR_REQUISITION_LINE",
        "LINE_ID", "number", [
            item(43, "PR_ID", "No. PR (DRAFT/REJECTED)", "select", req=True, dtype="number", lov="@editable-prs"),
            item(43, "LINE_NO", "No. Baris", "display", dtype="number", query_only=True),
            item(43, "ITEM_ID", "Item", "select", req=True, dtype="number", lov="@items"),
            item(43, "QTY", "Qty", "number", req=True, dtype="number", min_value=0),
            item(43, "UNIT_PRICE", "Estimasi Harga Satuan", "number", req=True, dtype="number", default_static="0",
                 min_value=0),
            item(43, "NOTES", "Catatan", "textarea", maxlen=500),
        ]))

    # ---------------------------------------------------------------- Inventory
    pagefile(50, "stock-transactions", ir_page(50, "Stock Transactions", "STOCK-TRANSACTIONS", "inventory",
        "stock-transactions", """
select txn_id, txn_no, txn_date, txn_type, bu_code, wh_code, item_code, item_name, uom, qty, qty_signed,
       unit_cost, total_cost, job_no, project_no, wbs_code, reference, notes, created_by
  from inv_stock_txn_v""",
        [("TXN_ID", "ID", "hidden"), ("TXN_NO", "No. Transaksi", "text"), ("TXN_DATE", "Tanggal", "date"),
         ("TXN_TYPE", "Tipe", "text"), ("BU_CODE", "BU", "text"), ("WH_CODE", "Gudang/Lokasi", "text"),
         ("ITEM_CODE", "Kode Item", "text"), ("ITEM_NAME", "Nama Item", "text"), ("UOM", "UoM", "text"),
         ("QTY", "Qty", "qty"), ("QTY_SIGNED", "Qty (+/-)", "qty"), ("UNIT_COST", "Biaya Satuan", "money"),
         ("TOTAL_COST", "Total Biaya", "money"), ("JOB_NO", "Job", "text"), ("PROJECT_NO", "Proyek", "text"),
         ("WBS_CODE", "WBS", "text"), ("REFERENCE", "Referensi", "text"), ("NOTES", "Catatan", "text"),
         ("CREATED_BY", "Dibuat Oleh", "text")],
        form_page=51, pk="TXN_ID", sort_col="TXN_NO", sort_desc=True, create_auth="warehouse-rights",
        help_text="Stock ledger: transaksi yang sudah diposting tidak dapat diubah/dihapus. Koreksi dengan transaksi ADJ_IN/ADJ_OUT/RETURN."))
    pagefile(51, "stock-transaction", form_page(51, "Stock Transaction", "STOCK-TRANSACTION", "inventory",
        "stock-transaction", "INV_STOCK_TXN", "TXN_ID", "number", [
            item(51, "TXN_NO", "No. Transaksi", "display", query_only=True),
            item(51, "TXN_DATE", "Tanggal", "date", req=True, dtype="date", default_sql="select trunc(sysdate) from dual"),
            item(51, "TXN_TYPE", "Tipe Transaksi", "select", req=True, lov="@txn-types", default_static="RECEIPT"),
            item(51, "WAREHOUSE_ID", "Gudang / Lokasi", "select", req=True, dtype="number", lov="@warehouses"),
            item(51, "ITEM_ID", "Item", "select", req=True, dtype="number", lov="@items"),
            item(51, "QTY", "Qty", "number", req=True, dtype="number", min_value=0),
            item(51, "UNIT_COST", "Biaya Satuan", "number", dtype="number", min_value=0,
                 help="Wajib untuk Receipt. Kosongkan untuk Issue/Return: dihitung dari biaya rata-rata."),
            item(51, "JOB_ID", "Job Order", "select", dtype="number", lov="@open-jobs",
                 help="Issue/Return wajib ke Job Order atau Proyek yang sudah approved (BR-05)."),
            item(51, "PROJECT_ID", "Proyek", "select", dtype="number", lov="@open-projects"),
            item(51, "WBS_ID", "WBS", "select", dtype="number", cascade="P51_PROJECT_ID",
                 lov="select wbs_code || ' - ' || wbs_name d, wbs_id r from prj_wbs where project_id = :P51_PROJECT_ID order by wbs_code"),
            item(51, "REFERENCE", "Referensi (PO/DO/BA)", maxlen=100),
            item(51, "NOTES", "Catatan", "textarea", maxlen=500),
        ], ops=("add",), auth="warehouse-rights",
        extra_validations=[
            val_expr("receipt-cost-required", "Biaya wajib untuk receipt", 10, ":P51_TXN_TYPE not in ('RECEIPT','ADJ_IN') or :P51_UNIT_COST is not null",
                     "Biaya satuan wajib diisi untuk Receipt / Adjustment (+).", "P51_UNIT_COST"),
            val_expr("issue-reference-required", "Referensi job/proyek untuk issue", 20, ":P51_TXN_TYPE not in ('ISSUE','RETURN') or :P51_JOB_ID is not null or :P51_PROJECT_ID is not null",
                     "Issue/Return wajib mereferensikan Job Order atau Proyek.", "P51_JOB_ID"),
        ]))

    pagefile(52, "stock-on-hand", ir_page(52, "Stock On Hand", "STOCK-ON-HAND", "inventory", "stock-on-hand", """
select bu_code, wh_code, wh_name, location_type, item_code, item_name, item_category, uom, min_stock,
       qty_on_hand, avg_cost, stock_value, below_min_yn
  from inv_stock_on_hand_v""",
        [("BU_CODE", "BU", "text"), ("WH_CODE", "Gudang/Lokasi", "text"), ("WH_NAME", "Nama Gudang", "text"),
         ("LOCATION_TYPE", "Tipe Lokasi", "text"), ("ITEM_CODE", "Kode Item", "text"), ("ITEM_NAME", "Nama Item", "text"),
         ("ITEM_CATEGORY", "Kategori", "text"), ("UOM", "UoM", "text"), ("MIN_STOCK", "Min. Stok", "qty"),
         ("QTY_ON_HAND", "On Hand", "qty"), ("AVG_COST", "Biaya Rata-rata", "money"),
         ("STOCK_VALUE", "Nilai Stok", "money"), ("BELOW_MIN_YN", "Di Bawah Min?", "text")],
        sort_col="ITEM_CODE"))

    # ---------------------------------------------------------------- Approval
    pagefile(60, "approval-inbox", ir_page(60, "Approval Inbox", "APPROVAL-INBOX", "approval", "approvals", """
select approval_id, doc_name, doc_no, bu_code, approval_level, approver_role, amount, requested_by,
       requested_on, status, can_act_yn, acted_by, acted_on, note
  from sys_approval_v""",
        [("APPROVAL_ID", "ID", "hidden"), ("DOC_NAME", "Jenis Dokumen", "text"), ("DOC_NO", "No. Dokumen", "text"),
         ("BU_CODE", "BU", "text"), ("APPROVAL_LEVEL", "Level", "num"), ("APPROVER_ROLE", "Role Approver", "text"),
         ("AMOUNT", "Nilai", "money"), ("REQUESTED_BY", "Diajukan Oleh", "text"), ("REQUESTED_ON", "Diajukan", "date"),
         ("STATUS", "Status", "text"), ("CAN_ACT_YN", "Bisa Saya Proses?", "text"), ("ACTED_BY", "Diproses Oleh", "text"),
         ("ACTED_ON", "Diproses", "date"), ("NOTE", "Catatan", "text")],
        form_page=61, pk="APPROVAL_ID", create=False, sort_col="APPROVAL_ID", sort_desc=True,
        help_text="Approval engine generik (Blueprint 6.1). Pengaju tidak dapat menyetujui dokumennya sendiri (maker-checker)."))
    appr_items = [
        item(61, "DOC_NAME", "Jenis Dokumen", "display"),
        item(61, "DOC_NO", "No. Dokumen", "display"),
        item(61, "BU_CODE", "BU", "display"),
        item(61, "APPROVAL_LEVEL", "Level", "display", dtype="number"),
        item(61, "APPROVER_ROLE", "Role Approver", "display"),
        item(61, "AMOUNT", "Nilai", "display", dtype="number"),
        item(61, "REQUESTED_BY", "Diajukan Oleh", "display"),
        item(61, "STATUS", "Status", "display"),
        item(61, "CAN_ACT_YN", "Bisa Saya Proses", "display"),
    ]
    can_act = "mbms_approval.can_act_yn(:P61_APPROVAL_ID) = 'Y'"
    p61 = [("name", "Approval"), ("alias", "APPROVAL"), ("title", "Approval"), ("pageGroup", "@approval"),
           ("appearance", G(("pageMode", "modalDialog"), ("dialogTemplate", "@/modal-dialog"), ("templateOptions", "#DEFAULT#"))),
           ("dialog", G(("chained", False), ("resizable", True))),
           buttons_region(),
           Comp("region", "approval",
                ("name", "Approval"),
                ("type", "form"),
                ("source", G(("location", "localDatabase"), ("tableName", "SYS_APPROVAL_V"))),
                ("layout", G(("sequence", 10), ("slot", "contentBody"))),
                ("appearance", G(("template", "@/blank-with-attributes"), ("templateOptions", "#DEFAULT#"))))]
    pk61 = item(61, "APPROVAL_ID", "ID", "hidden", dtype="number")
    pk61["pk"] = True
    p61.append(form_item(pk61, "approval", 5))
    for i, spec in enumerate(appr_items):
        p61.append(form_item(spec, "approval", (i + 1) * 10))
    note = item(61, "NOTE", "Catatan (wajib bila Reject)", "textarea", maxlen=1000)
    p61.append(form_item(note, "approval", 200, form=False))
    p61 += [
        dialog_button("cancel", "CANCEL", "Close", 10, "close"),
        dialog_button("reject", "REJECT", "Reject", 20, "next", cond=can_act, danger=True,
                      confirm="Tolak dokumen ini?"),
        dialog_button("approve", "APPROVE", "Approve", 30, "next", hot=True, cond=can_act),
        cancel_da(),
        Comp("process", "initialize-form",
             ("name", "Initialize form Approval"),
             ("type", "formInitialization"),
             ("formRegion", "@approval"),
             ("execution", G(("sequence", 10), ("point", "beforeHeader")))),
        Comp("process", "approve",
             ("name", "Approve"),
             ("type", "executeCode"),
             ("source", G(("plsqlCode", ML("plsql", "mbms_approval.approve(p_approval_id => :P61_APPROVAL_ID, p_note => :P61_NOTE);")))),
             ("execution", G(("sequence", 10))),
             ("successMessage", G(("successMessage", "Dokumen disetujui."))),
             ("serverSideCondition", G(("whenButtonPressed", "@approve")))),
        Comp("process", "reject",
             ("name", "Reject"),
             ("type", "executeCode"),
             ("source", G(("plsqlCode", ML("plsql", "mbms_approval.reject(p_approval_id => :P61_APPROVAL_ID, p_note => :P61_NOTE);")))),
             ("execution", G(("sequence", 20))),
             ("successMessage", G(("successMessage", "Dokumen ditolak."))),
             ("serverSideCondition", G(("whenButtonPressed", "@reject")))),
        Comp("process", "close-dialog",
             ("name", "Close Dialog"),
             ("type", "closeDialog"),
             ("settings", G(("showSuccessMessages", True))),
             ("execution", G(("sequence", 50))),
             ("serverSideCondition", G(("type", "requestIsContainedInValue"), ("value", "APPROVE,REJECT")))),
    ]
    pagefile(61, "approval", Comp("page", "61", *p61))

    # ---------------------------------------------------------------- Administration
    pagefile(90, "users-roles", ir_page(90, "Users & Roles", "USERS-ROLES", "administration", "users-roles", """
select ur.user_role_id, ur.username, ur.role_code, r.role_name, ur.created_by, ur.created_on
  from sys_user_role ur
  join sys_role r on r.role_code = ur.role_code""",
        [("USER_ROLE_ID", "ID", "hidden"), ("USERNAME", "Username", "text"), ("ROLE_CODE", "Role", "text"),
         ("ROLE_NAME", "Nama Role", "text"), ("CREATED_BY", "Dibuat Oleh", "text"), ("CREATED_ON", "Dibuat", "date")],
        form_page=91, pk="USER_ROLE_ID", sort_col="USERNAME", auth="admin-rights",
        help_text="Selama belum ada user dengan role ADMIN, semua user dianggap ADMIN (mode bootstrap). Daftarkan diri Anda sebagai ADMIN terlebih dahulu."))
    pagefile(91, "user-role", form_page(91, "User Role", "USER-ROLE", "administration", "user-role", "SYS_USER_ROLE",
        "USER_ROLE_ID", "number", [
            item(91, "USERNAME", "Username (APEX)", req=True, maxlen=255, default_sql="select :APP_USER from dual"),
            item(91, "ROLE_CODE", "Role", "select", req=True, lov="@roles"),
        ], auth="admin-rights"))

    pagefile(92, "document-types", ir_page(92, "Document Types & Approval", "DOCUMENT-TYPES", "administration",
        "document-types", """
select doc_type, doc_name, prefix, approver1_role, approver2_role, level2_limit
  from sys_doc_type""",
        [("DOC_TYPE", "Kode", "text"), ("DOC_NAME", "Dokumen", "text"), ("PREFIX", "Prefix Nomor", "text"),
         ("APPROVER1_ROLE", "Approver 1", "text"), ("APPROVER2_ROLE", "Approver 2", "text"),
         ("LEVEL2_LIMIT", "Approver 2 bila nilai >", "money")],
        form_page=93, pk="DOC_TYPE", create=False, sort_col="DOC_TYPE", auth="admin-rights",
        help_text="Approval matrix dan prefix penomoran configurable (D-11). Format nomor: PREFIX-BU-TAHUN-0001."))
    pagefile(93, "document-type", form_page(93, "Document Type", "DOCUMENT-TYPE", "administration", "document-type",
        "SYS_DOC_TYPE", "DOC_TYPE", "varchar2", [
            item(93, "DOC_NAME", "Nama Dokumen", req=True, maxlen=100),
            item(93, "PREFIX", "Prefix Nomor", req=True, maxlen=10),
            item(93, "APPROVER1_ROLE", "Approver Level 1", "select", lov="@roles", null_text="- Tanpa approval -"),
            item(93, "APPROVER2_ROLE", "Approver Level 2", "select", lov="@roles", null_text="- Tidak ada -"),
            item(93, "LEVEL2_LIMIT", "Level 2 bila nilai melebihi", "number", req=True, dtype="number", min_value=0),
        ], ops=("update",), auth="admin-rights"))


# =============================================================================
# Main
# =============================================================================
def copy_example0():
    for rel in [".apex/apexlang.json", "deployments/default.json",
                "shared-components/component-settings.apx", "shared-components/build-options.apx",
                "shared-components/authentications.apx", "shared-components/static-files.apx",
                "shared-components/themes/universal-theme/theme.apx", "pages/p00000-global-page.apx",
                "pages/p09999-login.apx"]:
        dst = os.path.join(OUT, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(os.path.join(EXAMPLE0, rel), dst)
    shutil.copytree(os.path.join(EXAMPLE0, "shared-components", "static-files", "icons"),
                    os.path.join(OUT, "shared-components", "static-files", "icons"), dirs_exist_ok=True)


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    copy_example0()
    put("application.apx", render(application()))
    put("page-groups.apx", page_groups())
    put("shared-components/authorizations.apx", render(*authorizations()))
    put("shared-components/lists/lists.apx", render(nav_bar(), nav_menu()))
    put("shared-components/lovs/lovs.apx", render(*LOVS))
    put("shared-components/breadcrumbs/breadcrumbs.apx", render(breadcrumbs()))
    put("supporting-objects/supporting-objects.apx", render(Comp("supportingObject", None,
        ("advanced", G(("includeInAppExport", False))))))
    pages()
    for rel, content in FILES.items():
        dst = os.path.join(OUT, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "w", encoding="utf-8") as f:
            f.write(content)
    print("Generated %d files into %s" % (len(FILES), OUT))


if __name__ == "__main__":
    main()
