import re

def supper_float_n(num:float|int) -> str:
    """
        小于0小数位太大数据处理,默认处理成保留最小数据后两位;
        0.0000000123 -> 0.000000012
        1.00000123   -> 1.00
    """
    float_num = str(float(num))
    if num>=1:
        float_num_split = float_num.split(".")
        return float_num_split[0]+"."+float_num_split[1][:2]
    if num>=0.01:
        return float_num[:4]
    # 强制转成数字而不是科学计数法导致数字解析失败
    if "e" in float_num:
        num_split = float_num.split("-")
        float_num = "0." + (int(num_split[-1]) - 1) * "0" + num_split[0].replace(".", "")
    return re.findall("0\\.0.*?[1-9]{1,2}",float_num )[0]

