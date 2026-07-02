export type AboutContentType = 'text' | 'url'

export interface AboutLegalSection {
  enabled: boolean
  type: AboutContentType
  content: string
}

export interface AboutSupportSection {
  enabled: boolean
  url: string
}

export interface AboutOut {
  privacy: AboutLegalSection
  terms: AboutLegalSection
  support: AboutSupportSection
}

export interface AboutPayload {
  privacy?: Partial<AboutLegalSection>
  terms?: Partial<AboutLegalSection>
  support?: Partial<AboutSupportSection>
}
