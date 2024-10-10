import sqlite3
from datetime import datetime


def create_table(db_path, columns):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    create_table_query = "CREATE TABLE IF NOT EXISTS imas_testere ({})".format(
        ", ".join(["{} {}".format(col, dtype) for col, dtype in columns.items()])
    )
    cursor.execute(create_table_query)
    conn.commit()
    conn.close()


def insert_to_database(db_path, data, columns):
    create_table(db_path, columns)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Sütun adlarını ve veri sırasını kontrol et
    columns_str = ", ".join(columns.keys())
    placeholders = ", ".join(["?" for _ in columns.keys()])

    # Veriyi uygun sırayla tuple haline getir
    data_tuple = []

    if isinstance(data, dict):
        # Eğer 'data' bir dict ise sütun isimlerine göre veri çek
        for col in columns.keys():
            value = data.get(col, None)  # Eğer sütun ismi 'data' içinde yoksa None döner

            # Veri tipine göre uygun dönüştürme işlemi yap
            expected_type = columns[col].upper()

            if value is not None:
                if "INTEGER" in expected_type:
                    try:
                        value = int(value)
                    except ValueError:
                        print(f"ValueError: Sütun {col} için '{value}' int'e dönüştürülemiyor.")
                        raise
                elif "REAL" in expected_type:
                    try:
                        value = float(value)
                    except ValueError:
                        print(f"ValueError: Sütun {col} için '{value}' float'a dönüştürülemiyor.")
                        raise
                elif "TEXT" in expected_type:
                    value = str(value)
                elif "BYTE" in expected_type:
                    if isinstance(value, int):
                        value = format(value, '02x')  # Byte değerini hex'e çevir
                    else:
                        value = str(value)

            data_tuple.append(value)

    elif isinstance(data, list):
        # Eğer 'data' bir listeyse indeks numarasına göre sütun verilerini al
        for i, col in enumerate(columns.keys()):
            try:
                value = data[i]  # Listeden sırayla eleman al
            except IndexError:
                print(f"Uyarı: {col} sütunu için yeterli veri yok, None değeri kullanılacak.")
                value = None  # Eğer yeterli eleman yoksa None kullan

            # Veri tipine göre uygun dönüştürme işlemi yap
            expected_type = columns[col].upper()

            if value is not None:
                if "INTEGER" in expected_type:
                    try:
                        value = int(value)
                    except ValueError:
                        print(f"ValueError: Sütun {col} için '{value}' int'e dönüştürülemiyor.")
                        raise
                elif "REAL" in expected_type:
                    try:
                        value = float(value)
                    except ValueError:
                        print(f"ValueError: Sütun {col} için '{value}' float'a dönüştürülemiyor.")
                        raise
                elif "TEXT" in expected_type:
                    value = str(value)
                elif "BYTE" in expected_type:
                    if isinstance(value, int):
                        value = format(value, '02x')  # Byte değerini hex'e çevir
                    else:
                        value = str(value)

            data_tuple.append(value)

    else:
        print(f"Hata: 'data' bir dict veya list olmalı, ancak şu an {type(data)} tipinde.")
        return

    # Tüm veriyi tuple olarak hazırladık
    data_tuple = tuple(data_tuple)

    # print(f"Inserting data: {data_tuple}")
    # print(f"Using columns: {list(columns.keys())}")

    # SQL sorgusunu çalıştır
    cursor.execute(f'INSERT INTO imas_testere ({columns_str}) VALUES ({placeholders})', data_tuple)
    conn.commit()
    conn.close()


def write_to_text_file(data, text_file_path):
    if isinstance(data, dict):
        data = list(data.values())
    with open(text_file_path, "a") as file:
        file.write(", ".join(map(str, data)) + "\n")


def process_row(row_data, fuzzy_output_value=None):
    # Milisaniye hassasiyetinde zaman damgası ekle
    row_data['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
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
    row_data['ivme_olcer_x'] = row_data['ivme_olcer_x'] / 1.0
    row_data['ivme_olcer_y'] = row_data['ivme_olcer_y'] / 1.0
    row_data['ivme_olcer_z'] = row_data['ivme_olcer_z'] / 1.0
    row_data['serit_kesme_hizi'] = row_data['serit_kesme_hizi'] * 0.0754
    if row_data['serit_inme_hizi'] == 0:
        row_data['serit_inme_hizi'] = 0.0
    else:
        row_data['serit_inme_hizi'] = (row_data['serit_inme_hizi'] - 65535) * -0.06

    if row_data['inme_motor_akim_a'] > 15:
        row_data['inme_motor_akim_a'] = 655.35 - row_data['inme_motor_akim_a']

    if abs(row_data['serit_sapmasi']) > 1.5:
        row_data['serit_sapmasi'] = abs(row_data['serit_sapmasi']) - 655.35

    return row_data
