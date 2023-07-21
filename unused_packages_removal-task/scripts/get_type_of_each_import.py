def built_in_to_json(file_path):
    std_lib_modules = dict()
    with open(file_path, 'r') as file:
        for each in file:
            each = each.split("\n")[0]
            std_lib_modules[each] = "built-in"
    return std_lib_modules


def third_partyToJson(file_path):
    third_party_modules = dict()
    with open(file_path, 'r') as file:
        for each in file:
            each = each.split("\n")[0]
            third_party_modules[each] = "third-party"
    return third_party_modules


def final_json(file_path, built_in, third_party):
    result = dict()
    with open(file_path) as f:
        data = set(map(lambda x: x.strip(), f.readlines()))
        for each in data:
            each = each.split(".")[0]
            if each in built_in:
                result[each] = built_in[each]
            elif each in third_party:
                result[each] = third_party[each]
            else:
                result[each] = "others"
    return result


if __name__ == '__main__':
    PATH_TO_TXT_BUILT_IN_MODULES_NAMES = "./data/modules_std_lib.txt"
    PATH_TO_TXT_THIRD_PARTY_MODULES_NAMES = "./data/modules_third_party_deepstream.txt"
    PATH_TO_TXT_FILE_WITH_COLLECTED_MODULES_NAMES = "./new.txt"
    PATH_TO_OUTPUT_TXT_FILE = "./module_sources.csv"

    built_in = built_in_to_json(PATH_TO_TXT_BUILT_IN_MODULES_NAMES)
    third_party = third_partyToJson(PATH_TO_TXT_THIRD_PARTY_MODULES_NAMES)
    # print(final_json("./main_proc_mgr.txt", built_in, third_party))
    # print(final_json("./backend.txt", built_in, third_party))
    dict_modules_collected_sources = final_json(PATH_TO_TXT_FILE_WITH_COLLECTED_MODULES_NAMES,
                                                built_in=built_in, third_party=third_party)

    with open(PATH_TO_OUTPUT_TXT_FILE, 'w') as f:
        for key in sorted(dict_modules_collected_sources.keys(), key=lambda x: x.lower()):
            f.write(f"{key},{dict_modules_collected_sources[key]}\n")
