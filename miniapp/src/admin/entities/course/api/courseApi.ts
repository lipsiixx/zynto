import { req, reqForm } from '@/admin/shared/api/adminApi'
import type { CourseOut, CoursePayload } from '../model/types'

export function getCourse(): Promise<CourseOut> {
  return req('GET', '/course')
}

export function updateCourse(payload: CoursePayload): Promise<CourseOut> {
  return req('PUT', '/course', payload)
}

export function uploadCourseVideo(video: File): Promise<{ ok: true }> {
  const form = new FormData()
  form.set('video', video)
  return reqForm('POST', '/course/video', form)
}
