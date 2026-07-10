from rest_framework.serializers import Serializer

def serializer_formatter(serializer:Serializer):
    '''
    required_filed:
    {'codeId': [ErrorDetail(string='This field is required.', code='required')]}
    all_filed  = serializer.fields
    {'name': CharField(label='项目名称', max_length=100, required=False), 'display_name': CharField(label='项目显示名称', max_length=100, required=False), 'codeId': CharField(label='项目代码', max_length=100, required=True)}
    params
    {'name': 'a'}
    '''
    required_filed = serializer.errors
    all_filed  = serializer.fields
    params = serializer.get_initial()
    for filed_name,filed_value in required_filed.items():
        filed = all_filed[filed_name]
        label = filed.label or filed.field_name
        message = ""
        if filed_name not in params:
            if isinstance(filed_value,list):
                message = ''.join([str(error) for error in filed_value])
            else:
                message = str(filed_value)

        return "{label}:{message}".format(label=label,message=message)
