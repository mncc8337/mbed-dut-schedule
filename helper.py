import time

def get_time():
    return time.time() + 946684800

def quote_plus(s):
    safe_chars = safe_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.~"
    result = []
    for ch in s:
        if ch in safe_chars:
            result.append(ch)
        elif ch == ' ':
            result.append('+')
        else:
            result.append('%{:02X}'.format(ord(ch)))
    return ''.join(result)

def html_unescape(s):
    s = s.replace("&lt;", "<")
    s = s.replace("&gt;", ">")
    s = s.replace("&amp;", "&")
    s = s.replace("&quot;", '"')
    s = s.replace("&#39;", "'")
    return s

def get_hidden_field(html, field_name):
    name_str = 'name="' + field_name + '"'
    i = html.find(name_str)
    if i == -1:
        return None
    val_start = html.find('value="', i)
    if val_start == -1:
        return None
    val_start += len('value="')
    val_end = html.find('"', val_start)
    return html[val_start:val_end]

def extract_table_html(html, table_id):
    search = 'id="{}"'.format(table_id)
    start = html.find('<table')
    while start != -1:
        # find the next table tag that has the correct id
        tag_end = html.find('>', start)
        if tag_end == -1:
            return None
        table_tag = html[start:tag_end+1]
        if search in table_tag or "id='{}'".format(table_id) in table_tag:
            # found correct table
            end = html.find('</table>', tag_end)
            if end == -1:
                return None
            return html[start:end+8]  # include </table>
        # continue searching for next <table>
        start = html.find('<table', tag_end)
    return None

def parse_table_rows(table_html):
    rows = []
    pos = 0

    while True:
        # find next <tr>
        tr_start = table_html.find("<tr", pos)
        if tr_start == -1:
            break
        tr_start = table_html.find(">", tr_start)
        if tr_start == -1:
            break
        tr_end = table_html.find("</tr>", tr_start)
        if tr_end == -1:
            break

        tr_inner = table_html[tr_start + 1:tr_end]
        pos = tr_end + 5

        # extract <td> or <th> cells manually
        cells = []
        cell_pos = 0
        while True:
            td_start = tr_inner.find("<t", cell_pos)
            if td_start == -1:
                break
            td_close = tr_inner.find(">", td_start)
            if td_close == -1:
                break
            td_end = tr_inner.find("</t", td_close)
            if td_end == -1:
                break

            cell_html = tr_inner[td_close + 1:td_end].strip()
            # remove any inner tags (simple and safe)
            clean = ""
            in_tag = False
            for ch in cell_html:
                if ch == "<":
                    in_tag = True
                elif ch == ">":
                    in_tag = False
                elif not in_tag:
                    clean += ch
            clean = " ".join(clean.split())
            clean = html_unescape(clean)

            cells.append(clean)
            cell_pos = td_end + 4

        if cells:
            rows.append(cells)

    return rows
