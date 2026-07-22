import axios from 'axios'


// 创建axios实例
const httpInstance = axios.create({
  baseURL: 'http://localhost:8000/',
  timeout: 2000
})

// axios请求拦截器
httpInstance.interceptors.request.use(config => {
    //这里可以对请求处理
  return config
}, e => Promise.reject(e))

// axios响应式拦截器
httpInstance.interceptors.response.use(res => {
    //这里可以对响应处理
    return res.data
}, e => {
  return Promise.reject(e)
})

export default httpInstance
