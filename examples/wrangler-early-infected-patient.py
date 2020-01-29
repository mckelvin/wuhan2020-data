import os
import re
import sys
import datetime

RE_PATIENT_ID = re.compile("(患者|病例)([^，]*)，")
RE_AGE = re.compile("(\d+)岁")
RE_GENDER = re.compile("，([男女])[，、]")
RE_CONTACT_INFO = re.compile("(\d{1,2})月(\d{1,2})日[与在至]([^，]*)，")
RE_TRAVEL_INFO = re.compile("(\d{1,2})月(\d{1,2})日(乘[^从自离]+)?[从自离]?([^，返]*)(回|返回|到达|前往|来)([^，的]*)")
RE_SYMPTOM_DATE = re.compile(
    "(\d{1,2})月(\d{1,2})日?[^，]*"
    "(出现|自觉|自感|收到|查CT|自发就诊|返回.*当天出现|通过排查发现|发热|发烧|患者出现|在?.*发病)"
)
RE_TEMPERATURE = re.compile("体温([\.0-9]*)")
RE_CURR_LOCATION = re.compile("现[住在]([^，]*[市区县])，")

CITY_DICT = {
    "萧山机场": "杭州",
}


def parse_patient_line(province, city, date, flag_text, line):
    # ID 
    _, patient_id = RE_PATIENT_ID.findall(line)[0]
    if flag_text == "累计":
        global_patient_id = f"{province}{city}{patient_id}"
    elif flag_text == "新增":
        global_patient_id = f"{province}{city}{date:%Y-%m-%d}{flag_text}{patient_id}"
    age = RE_AGE.findall(line)[0]
    gender = RE_GENDER.findall(line)[0]

    extracted = {
        "_raw": line,
        "global_patient_id": global_patient_id,
        "age": age,
        "gender": gender,
    }

    # 症状出现日期
    symptom_data = RE_SYMPTOM_DATE.findall(line)
    assert len(symptom_data) <= 1
    if symptom_data:
        spm, spd, _ = symptom_data[0]
        spm = int(spm)
        spd = int(spd)
        symptom_date = datetime.date(2020 if spm <= 6 else 2019, spm, spd)
        extracted["symptom_date"] = symptom_date

    # 所在地
    curr_location = RE_CURR_LOCATION.findall(line)
    if curr_location:
        extracted["curr_location"] = curr_location[0]

    # 旅游史
    travel_data = RE_TRAVEL_INFO.findall(line)
    if travel_data:
        for mvm, mvd, _, mvsrc, _, mvdst in travel_data:
            mvm = int(mvm)
            mvd = int(mvd)
            if len(mvsrc) == 1 and city.startswith(mvsrc):
                mvsrc = city
            if len(mvdst) == 1 and city.startswith(mvdst):
                mvdst = city
            extracted.setdefault("travel_info", []).append({
                "date": datetime.date(2020 if mvm <= 6 else 2019, mvm, mvd),
                "from": CITY_DICT.get(mvsrc, mvsrc),
                "to": CITY_DICT.get(mvdst, mvdst),
            })

    # 体温
    temperature = RE_TEMPERATURE.findall(line)
    if temperature:
        extracted["temperature"] = temperature[0]

    # 接触史
    contact_info = RE_CONTACT_INFO.findall(line)
    if contact_info:
        extracted["contact_info"] = contact_info

    return extracted


def parse_file(file_path):
    """
    file_path Example:
        "[...]/浙江/温州/确诊病例情况/2020-01-27-新增.txt"
    """

    abspath = os.path.abspath(file_path)
    filename = os.path.basename(abspath)

    pdir = os.path.dirname(abspath)
    assert os.path.basename(pdir) == "确诊病例情况"
    city_dir = os.path.dirname(pdir)
    city_name = os.path.basename(city_dir)
    province_dir = os.path.dirname(city_dir)
    province_name = os.path.basename(province_dir)
 
    filename_prefix, ext = os.path.splitext(filename)
    assert ext == ".txt"
    year, month, day, flag_text = filename_prefix.split("-", 3)

    with open(file_path, "r") as fhandler:
        for line in fhandler:
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                continue
            try:
                patient_dict = parse_patient_line(
                    province_name,
                    city_name,
                    datetime.date(int(year), int(month), int(day)),
                    flag_text,
                    line
                )
            except Exception as ex:
                print(f"Failed to parse {line}", file=sys.stderr)
                raise ex
            yield patient_dict


def main(argv):
    if len(argv) >= 2:
        input_files = argv[1:]
    else:
        print("Usage: python3 this.py raw-data/浙江/温州/确诊病例情况/*.txt", file=sys.stderr)
        return 1

    for input_file in input_files:
        print(f"# Input: {input_file}", file=sys.stderr)
        for sample in parse_file(input_file):
            """
            from_city = None
            if "travel_info" in sample:
                from_city = sample["travel_info"]["from"]
            """
            symptom_date = sample.get("symptom_date")

            if symptom_date is None or symptom_date < datetime.date(2020, 1, 10):
                print(sample.pop("_raw"), file=sys.stderr)
                print(sample)
                print()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
