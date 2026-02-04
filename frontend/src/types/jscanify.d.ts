declare module 'jscanify/client' {
  export default class Scanner {
    constructor();
    findPaperContour(img: any): any;
    getCornerPoints(contour: any): { topLeftCorner: any; topRightCorner: any; bottomLeftCorner: any; bottomRightCorner: any } | null;
    extractPaper(img: any, resultWidth: number, resultHeight: number): HTMLCanvasElement;
    highlightPaper(img: any, options?: { color?: string; thickness?: number }): HTMLCanvasElement;
  }
}

interface Window {
  cv: any;
}
