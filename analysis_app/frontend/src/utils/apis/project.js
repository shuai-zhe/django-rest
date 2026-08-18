import request from "../request"

export const ProjectList=(params = {})=>{
    return request.get( 
        "/gate/project",
        { params }
    )
}

export const ProjectKline=(params)=>{
    return request.get(
        "/gate/project/kline",
        { params }
    )
}