import request from "../request"

export const ProjectList=()=>{
    return request.get( 
        "/gate/project"
    )
}