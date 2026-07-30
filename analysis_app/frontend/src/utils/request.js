import axios from 'axios'

const baseURL = import.meta.env.MODE === 'development'
  ? 'http://30.25.59.26:8001'
  : 'http://43.136.20.216:5001'

// 创建axios实例
const request = axios.create({
  baseURL: baseURL,
  timeout: 2000
})

// axios请求拦截器
request.interceptors.request.use(config => {
    //这里可以对请求处理
  return config
}, e => Promise.reject(e))

// axios响应式拦截器
request.interceptors.response.use(res => {
    //这里可以对响应处理
    return res.data
}, e => {
  return Promise.reject(e)
})

export default request
