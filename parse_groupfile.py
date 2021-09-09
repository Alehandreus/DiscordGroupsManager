from openpyxl import load_workbook


def get_groups(filename):
    workbook = load_workbook(filename=filename)
    groups = []

    for sheet in workbook:
        group_title = sheet['A1'].value
        group_members = []
        group_admins = []

        row = 2
        while name := sheet[f'A{row}'].value:
            if sheet[f'A{row}'].font.bold:
                group_admins.append(name)
            else:
                group_members.append(name)
            row += 1

        group = {
            "title": group_title,
            "members": group_members,
            "admins": group_admins,
        }
        groups.append(group)

    return groups
