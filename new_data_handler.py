import sqlite3


def create_table(db_path, columns):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    create_table_query = "CREATE TABLE IF NOT EXISTS imas_testere ({})".format(
        ", ".join(["{} {}".format(col, dtype) for col, dtype in columns.items()])
    )
    cursor.execute(create_table_query)
    conn.commit()
    conn.close()


def clean_data(data, columns):
    """
    Gelen verileri temizler:
    - Fazla sütunları (DB'de olmayanları) çıkarır.
    - Aynı verinin çoklanmasını engeller.
    """
    cleaned_data = {}

    # Fazladan gelen sütunları kontrol ediyoruz
    for col in columns.keys():
        if col in data:
            cleaned_data[col] = data[col]  # DB'deki sütunlara göre ayıklanmış veriler
        else:
            print(f"Warning: '{col}' column is missing in the incoming data. Using None for this column.")
            cleaned_data[col] = None  # Eksik sütunlar varsa None kullanıyoruz

    return cleaned_data


def insert_to_database(db_path, data, columns):
    create_table(db_path, columns)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Veriyi temizle
    cleaned_data = clean_data(data, columns)

    # Veritabanına uygun sütun adları ve placeholder'ları oluştur
    columns_str = ", ".join(columns.keys())
    placeholders = ", ".join(["?" for _ in columns])

    # Veriyi tuple formatına çeviriyoruz
    data_tuple = tuple(cleaned_data.values())

    # Veriyi DB'ye ekliyoruz
    cursor.execute(f'INSERT INTO imas_testere ({columns_str}) VALUES ({placeholders})', data_tuple)
    conn.commit()
    conn.close()


def write_to_text_file(data, text_file_path):
    if isinstance(data, dict):
        data = list(data.values())
    with open(text_file_path, "a") as file:
        file.write(", ".join(map(str, data)) + "\n")


def process_row(row_data, fuzzy_output_value=None):
    # Verileri normalize etme işlemleri
    row_data['testere_durumu'] = int(row_data['testere_durumu'])
    row_data['alarm_status'] = int(row_data['alarm_status'])
    row_data['alarm_bilgisi'] = f"0x{int(row_data['alarm_bilgisi']):04x}"
    row_data['kafa_yuksekligi_mm'] = row_data['kafa_yuksekligi_mm'] / 10.0
    row_data['serit_motor_akim_a'] = row_data['serit_motor_akim_a'] / 10.0
    row_data['serit_motor_tork_percentage'] = row_data['serit_motor_tork_percentage'] / 10.0
    row_data['inme_motor_akim_a'] = row_data['inme_motor_akim_a'] / 100.0
    row_data['mengene_basinc_bar'] = row_data['mengene_basinc_bar'] / 10.0
    row_data['serit_gerginligi_bar'] = row_data['serit_gerginligi_bar'] / 10.0
    row_data['serit_sapmasi'] = row_data['serit_sapmasi'] / 100.0
    row_data['ortam_sicakligi_c'] = row_data['ortam_sicakligi_c'] / 10.0
    row_data['ortam_nem_percentage'] = row_data['ortam_nem_percentage'] / 10.0
    row_data['sogutma_sivi_sicakligi_c'] = row_data['sogutma_sivi_sicakligi_c'] / 10.0
    row_data['hidrolik_yag_sicakligi_c'] = row_data['hidrolik_yag_sicakligi_c'] / 10.0
    row_data['ivme_olcer_x'] = row_data['ivme_olcer_x'] / 10.0
    row_data['ivme_olcer_y'] = row_data['ivme_olcer_y'] / 10.0
    row_data['ivme_olcer_z'] = row_data['ivme_olcer_z'] / 10.0
    row_data['serit_kesme_hizi'] = row_data['serit_kesme_hizi'] * 0.0754

    if row_data['serit_inme_hizi'] == 0:
        row_data['serit_inme_hizi'] = 0.0
    else:
        row_data['serit_inme_hizi'] = (row_data['serit_inme_hizi'] - 65535) * -0.06

    if row_data['inme_motor_akim_a'] > 15:
        row_data['inme_motor_akim_a'] = 655.35 - row_data['inme_motor_akim_a']

    if abs(row_data['serit_sapmasi']) > 1.5:
        row_data['serit_sapmasi'] = abs(row_data['serit_sapmasi']) - 655.35

    row_data['fuzzy_output'] = fuzzy_output_value
    # print(row_data)
    return row_data
