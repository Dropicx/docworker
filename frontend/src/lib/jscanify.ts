/**
 * Document scanner using OpenCV.js — based on jscanify (MIT License)
 * Original: https://github.com/nicovince/jscanify
 * Inlined to avoid native dependency (canvas/node-gyp) issues in Docker builds.
 */

/* eslint-disable @typescript-eslint/no-explicit-any */

interface Point {
  x: number;
  y: number;
}

export interface CornerPoints {
  topLeftCorner: Point;
  topRightCorner: Point;
  bottomLeftCorner: Point;
  bottomRightCorner: Point;
}

function distance(p1: Point, p2: Point): number {
  return Math.hypot(p1.x - p2.x, p1.y - p2.y);
}

function getCv(): any {
  return (window as any).cv;
}

export default class Scanner {
  /**
   * Finds the largest contour (paper outline) in the image.
   * @param img cv.Mat to process
   * @returns largest contour as cv.Mat, or null if none found
   */
  findPaperContour(img: any): any | null {
    const cv = getCv();
    const imgGray = new cv.Mat();
    cv.Canny(img, imgGray, 50, 200);

    const imgBlur = new cv.Mat();
    cv.GaussianBlur(imgGray, imgBlur, new cv.Size(3, 3), 0, 0, cv.BORDER_DEFAULT);

    const imgThresh = new cv.Mat();
    cv.threshold(imgBlur, imgThresh, 0, 255, cv.THRESH_OTSU);

    const contours = new cv.MatVector();
    const hierarchy = new cv.Mat();
    cv.findContours(imgThresh, contours, hierarchy, cv.RETR_CCOMP, cv.CHAIN_APPROX_SIMPLE);

    let maxArea = 0;
    let maxContourIndex = -1;
    for (let i = 0; i < contours.size(); ++i) {
      const area = cv.contourArea(contours.get(i));
      if (area > maxArea) {
        maxArea = area;
        maxContourIndex = i;
      }
    }

    const maxContour = maxContourIndex >= 0 ? contours.get(maxContourIndex) : null;

    imgGray.delete();
    imgBlur.delete();
    imgThresh.delete();
    contours.delete();
    hierarchy.delete();
    return maxContour;
  }

  /**
   * Extracts and perspective-corrects the detected paper region.
   * @returns HTMLCanvasElement with the corrected image, or null if no paper detected
   */
  extractPaper(
    image: HTMLCanvasElement,
    resultWidth: number,
    resultHeight: number,
    cornerPoints?: CornerPoints
  ): HTMLCanvasElement | null {
    const cv = getCv();
    const canvas = document.createElement('canvas');
    const img = cv.imread(image);
    const maxContour = cornerPoints ? null : this.findPaperContour(img);

    if (maxContour == null && cornerPoints === undefined) {
      img.delete();
      return null;
    }

    const corners = cornerPoints || this.getCornerPoints(maxContour);
    if (!corners) {
      img.delete();
      if (maxContour) maxContour.delete();
      return null;
    }

    const { topLeftCorner, topRightCorner, bottomLeftCorner, bottomRightCorner } = corners;

    const warpedDst = new cv.Mat();
    const dsize = new cv.Size(resultWidth, resultHeight);

    const srcTri = cv.matFromArray(4, 1, cv.CV_32FC2, [
      topLeftCorner.x, topLeftCorner.y,
      topRightCorner.x, topRightCorner.y,
      bottomLeftCorner.x, bottomLeftCorner.y,
      bottomRightCorner.x, bottomRightCorner.y,
    ]);

    const dstTri = cv.matFromArray(4, 1, cv.CV_32FC2, [
      0, 0,
      resultWidth, 0,
      0, resultHeight,
      resultWidth, resultHeight,
    ]);

    const M = cv.getPerspectiveTransform(srcTri, dstTri);
    cv.warpPerspective(img, warpedDst, M, dsize, cv.INTER_LINEAR, cv.BORDER_CONSTANT, new cv.Scalar());
    cv.imshow(canvas, warpedDst);

    img.delete();
    warpedDst.delete();
    srcTri.delete();
    dstTri.delete();
    M.delete();
    return canvas;
  }

  /**
   * Calculates corner points from a contour.
   */
  getCornerPoints(contour: any): CornerPoints | null {
    const cv = getCv();
    if (!contour) return null;

    const rect = cv.minAreaRect(contour);
    const center = rect.center;

    let topLeftCorner: Point | undefined;
    let topLeftCornerDist = 0;
    let topRightCorner: Point | undefined;
    let topRightCornerDist = 0;
    let bottomLeftCorner: Point | undefined;
    let bottomLeftCornerDist = 0;
    let bottomRightCorner: Point | undefined;
    let bottomRightCornerDist = 0;

    for (let i = 0; i < contour.data32S.length; i += 2) {
      const point: Point = { x: contour.data32S[i], y: contour.data32S[i + 1] };
      const dist = distance(point, center);

      if (point.x < center.x && point.y < center.y) {
        if (dist > topLeftCornerDist) {
          topLeftCorner = point;
          topLeftCornerDist = dist;
        }
      } else if (point.x > center.x && point.y < center.y) {
        if (dist > topRightCornerDist) {
          topRightCorner = point;
          topRightCornerDist = dist;
        }
      } else if (point.x < center.x && point.y > center.y) {
        if (dist > bottomLeftCornerDist) {
          bottomLeftCorner = point;
          bottomLeftCornerDist = dist;
        }
      } else if (point.x > center.x && point.y > center.y) {
        if (dist > bottomRightCornerDist) {
          bottomRightCorner = point;
          bottomRightCornerDist = dist;
        }
      }
    }

    if (!topLeftCorner || !topRightCorner || !bottomLeftCorner || !bottomRightCorner) {
      return null;
    }

    return { topLeftCorner, topRightCorner, bottomLeftCorner, bottomRightCorner };
  }
}
