import axios from 'axios'

const baseURL = import.meta.env.VITE_API_BASE || ''

export const http = axios.create({ baseURL, timeout: 20000 })

http.interceptors.response.use(
  (resp) => resp,
  (err) => {
    const msg = err?.response?.data?.error || err.message || '网络错误'
    return Promise.reject(new Error(msg))
  }
)