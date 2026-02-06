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

// Detection constants for document filtering
const MIN_AREA_RATIO = 0.05;      // Contour must be at least 5% of frame
const MAX_AREA_RATIO = 0.98;      // Not full frame
const EPSILON_FACTOR = 0.04;      // Polygon approximation tolerance (more lenient)
const MIN_ASPECT_RATIO = 0.4;     // Allow portrait documents (A4 portrait ~ 0.71)
const MAX_ASPECT_RATIO = 2.5;     // Allow various document sizes

export default class Scanner {
  /**
   * Finds the paper contour in the image using quadrilateral detection.
   * Filters for document-like shapes (4 corners, proper aspect ratio, convex).
   * @param img cv.Mat to process
   * @returns paper contour as cv.Mat, or null if none found
   */
  findPaperContour(img: any): any | null {
    const cv = getCv();

    // Try Canny edge detection first
    let result = this.findContourWithCanny(img, cv);

    // If Canny fails, try threshold-based detection for white paper
    if (!result) {
      result = this.findContourWithThreshold(img, cv);
    }

    return result;
  }

  /**
   * Find paper contour using Canny edge detection
   */
  private findContourWithCanny(img: any, cv: any): any | null {
    const frameArea = img.rows * img.cols;
    const minArea = frameArea * MIN_AREA_RATIO;
    const maxArea = frameArea * MAX_AREA_RATIO;

    // Convert to grayscale
    const gray = new cv.Mat();
    cv.cvtColor(img, gray, cv.COLOR_RGBA2GRAY);

    // Apply moderate Gaussian blur to reduce noise
    const blurred = new cv.Mat();
    cv.GaussianBlur(gray, blurred, new cv.Size(5, 5), 0);

    // Canny edge detection with lower thresholds for white paper detection
    const edges = new cv.Mat();
    cv.Canny(blurred, edges, 30, 100);

    // Morphological closing with larger kernel to connect broken edges
    const kernel = cv.Mat.ones(7, 7, cv.CV_8U);
    const dilated = new cv.Mat();
    const closed = new cv.Mat();
    cv.dilate(edges, dilated, kernel);
    cv.erode(dilated, closed, kernel);

    // Find contours
    const contours = new cv.MatVector();
    const hierarchy = new cv.Mat();
    cv.findContours(closed, contours, hierarchy, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE);

    const bestContour = this.findBestQuadrilateral(contours, cv, minArea, maxArea, frameArea);

    // Cleanup
    gray.delete();
    blurred.delete();
    edges.delete();
    kernel.delete();
    dilated.delete();
    closed.delete();
    contours.delete();
    hierarchy.delete();

    return bestContour;
  }

  /**
   * Find paper contour using threshold-based detection (for white paper)
   */
  private findContourWithThreshold(img: any, cv: any): any | null {
    const frameArea = img.rows * img.cols;
    const minArea = frameArea * MIN_AREA_RATIO;
    const maxArea = frameArea * MAX_AREA_RATIO;

    // Convert to grayscale
    const gray = new cv.Mat();
    cv.cvtColor(img, gray, cv.COLOR_RGBA2GRAY);

    // Apply Gaussian blur
    const blurred = new cv.Mat();
    cv.GaussianBlur(gray, blurred, new cv.Size(5, 5), 0);

    // Use Otsu's threshold to find bright regions (white paper)
    const thresh = new cv.Mat();
    cv.threshold(blurred, thresh, 0, 255, cv.THRESH_BINARY + cv.THRESH_OTSU);

    // Morphological operations to clean up
    const kernel = cv.Mat.ones(5, 5, cv.CV_8U);
    const morphed = new cv.Mat();
    cv.morphologyEx(thresh, morphed, cv.MORPH_CLOSE, kernel);

    // Find contours
    const contours = new cv.MatVector();
    const hierarchy = new cv.Mat();
    cv.findContours(morphed, contours, hierarchy, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE);

    const bestContour = this.findBestQuadrilateral(contours, cv, minArea, maxArea, frameArea);

    // Cleanup
    gray.delete();
    blurred.delete();
    thresh.delete();
    kernel.delete();
    morphed.delete();
    contours.delete();
    hierarchy.delete();

    return bestContour;
  }

  /**
   * Find the best quadrilateral contour from a list of contours
   */
  private findBestQuadrilateral(
    contours: any,
    cv: any,
    minArea: number,
    maxArea: number,
    frameArea: number
  ): any | null {
    let bestContour: any = null;
    let bestScore = 0;

    for (let i = 0; i < contours.size(); i++) {
      const contour = contours.get(i);
      const area = cv.contourArea(contour);

      // Check area bounds
      if (area < minArea || area > maxArea) {
        contour.delete();
        continue;
      }

      // Try multiple epsilon values to find a quadrilateral
      const peri = cv.arcLength(contour, true);
      let approx: any = null;

      // Try epsilon values from strict to lenient
      for (const epsilon of [0.02, 0.03, 0.04, 0.05, 0.06]) {
        const candidate = new cv.Mat();
        cv.approxPolyDP(contour, candidate, epsilon * peri, true);

        if (candidate.rows === 4 && cv.isContourConvex(candidate)) {
          approx = candidate;
          break;
        }
        candidate.delete();
      }

      // Must be a quadrilateral (exactly 4 corners) and convex
      if (!approx) {
        contour.delete();
        continue;
      }

      // Check aspect ratio using bounding rect
      const rect = cv.boundingRect(approx);
      const aspectRatio = rect.width / rect.height;
      if (aspectRatio < MIN_ASPECT_RATIO || aspectRatio > MAX_ASPECT_RATIO) {
        approx.delete();
        contour.delete();
        continue;
      }

      // Score: prioritize larger area (paper should be biggest quadrilateral)
      const areaScore = area / frameArea;
      const score = areaScore;

      if (score > bestScore) {
        if (bestContour) bestContour.delete();
        bestContour = approx;
        bestScore = score;
      } else {
        approx.delete();
      }

      contour.delete();
    }

    return bestContour;
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
   * Handles both 4-point approximated contours and general contours.
   */
  getCornerPoints(contour: any): CornerPoints | null {
    if (!contour) return null;

    // Extract points from contour
    const points: Point[] = [];
    for (let i = 0; i < contour.data32S.length; i += 2) {
      points.push({ x: contour.data32S[i], y: contour.data32S[i + 1] });
    }

    // If we have exactly 4 points (from approxPolyDP), sort them directly
    if (points.length === 4) {
      // Sort by y first (top vs bottom), then by x (left vs right)
      const sorted = [...points].sort((a, b) => a.y - b.y);
      const topTwo = sorted.slice(0, 2).sort((a, b) => a.x - b.x);
      const bottomTwo = sorted.slice(2, 4).sort((a, b) => a.x - b.x);

      return {
        topLeftCorner: topTwo[0],
        topRightCorner: topTwo[1],
        bottomLeftCorner: bottomTwo[0],
        bottomRightCorner: bottomTwo[1],
      };
    }

    // For general contours, use center-based assignment
    const cv = getCv();
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

    for (const point of points) {
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
