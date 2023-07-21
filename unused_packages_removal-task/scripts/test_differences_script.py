

def get_installed(file_path):
    data = dict()
    with open(file_path,'r') as file:
        for each in file:
            data[each] = "installed"
    return data

def get_company(file_path):
    data = dict()
    with open(file_path,'r') as file:
        for each in file:
            data[each] = "company"
    return data

def get_final_list(i_file_path,c_file_path,file_path):
    installed = get_installed(i_file_path)
    company = get_company(c_file_path)
    both = dict()
    
    for each in company:
        if each in installed:
            both[each] = "both"
            company[each] = "both"
            installed[each] = "both"
    
    new_installed,new_company = dict(),dict()
    for each in company:
        if company[each] == "company":
            new_company[each] = "company"
    for each in installed:
        if installed[each] == "installed":
            new_installed[each] = "installed"

    with open(file_path,'w') as file:
        both_len,installed_len,company_len = len(both),len(new_installed),len(new_company)

        file.write(f"{both_len} packages belongs to both \n \n")
        for each in both:
            file.write(f"{each}")

        file.write(f"\n \n{installed_len} packages belongs to installed \n \n")
        for each in new_installed:
            file.write(f"{each}")

        file.write(f"\n \n{company_len} packages belongs to company \n \n")
        for each in new_company:
            file.write(f"{each}")

if __name__=="__main__":
    get_final_list("./installed.txt","./company.txt","./test-differences.txt")
        