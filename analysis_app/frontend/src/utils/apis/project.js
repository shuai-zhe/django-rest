import request from "../request"

export const ProjectList=()=>{
    return request.get( 
        "/gate/project"
    )
}

export const ProjectKline=(params)=>{
    return request.get(
        "/gate/project/kline",
        { params }
    )
}