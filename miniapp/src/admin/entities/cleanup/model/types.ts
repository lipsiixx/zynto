export interface CleanupOut {
  /** 0 = хранить вечно. */
  text_retention_days: number
  media_retention_days: number
}

export interface CleanupPayload {
  text_retention_days?: number
  media_retention_days?: number
}
