export interface Photo {
  filename: string
  url: string
  width: number
  height: number
}

export interface GalleryResponse {
  photos: Photo[]
  total: number
}
