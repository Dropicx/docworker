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

export interface QualityWarning {
  type: 'blur' | 'skew' | 'glare' | 'incomplete' | 'tooSmall';
  message: string;
  severity: 'warning' | 'error';
}

export interface QualityResult {
  isAcceptable: boolean;
  warnings: QualityWarning[];
  blurScore: number;
  skewAngle: number;
  glarePercentage: number;
  documentCoverage: number;
}

export interface OrientationResult {
  rotation: 0 | 90 | 180 | 270;
  confidence: number; // 0-1
}

export interface ExtractPaperResult {
  canvas: HTMLCanvasElement;
  appliedSkewCorrection: number;
  detectedOrientation: OrientationResult;
  orientationCorrected: boolean;
}

function distance(p1: Point, p2: Point): number {
  return Math.hypot(p1.x - p2.x, p1.y - p2.y);
}

function angleBetweenVectors(v1: Point, v2: Point): number {
  const dot = v1.x * v2.x + v1.y * v2.y;
  const mag1 = Math.hypot(v1.x, v1.y);
  const mag2 = Math.hypot(v2.x, v2.y);
  if (mag1 === 0 || mag2 === 0) return 0;
  const cosAngle = Math.max(-1, Math.min(1, dot / (mag1 * mag2)));
  return Math.acos(cosAngle) * (180 / Math.PI);
}

function getCv(): any {
  return (window as any).cv;
}

// Detection constants for document filtering
const MIN_AREA_RATIO = 0.12;      // Paper must fill at least 12% of frame
const MAX_AREA_RATIO = 0.98;      // Not full frame
const EPSILON_FACTOR = 0.04;      // Polygon approximation tolerance (more lenient)
const MIN_ASPECT_RATIO = 0.5;     // A4 portrait ~ 0.71, allow more tolerance
const MAX_ASPECT_RATIO = 2.0;     // A4 landscape ~ 1.41, allow more tolerance
const CORNER_EDGE_MARGIN = 0.25;  // Corner within 25% of frame edge counts as "near edge"
const MIN_CORNERS_NEAR_EDGE = 2;  // At least 2 corners must be near frame edges (paper, not table)

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
    cv.Canny(blurred, edges, 50, 150);

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

    const bestContour = this.findBestQuadrilateral(contours, cv, minArea, maxArea, frameArea, img.cols, img.rows);

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

    const bestContour = this.findBestQuadrilateral(contours, cv, minArea, maxArea, frameArea, img.cols, img.rows);

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
   * Validates that all corners of the quadrilateral are approximately 90 degrees.
   * @param corners The four corner points
   * @param tolerance Maximum deviation from 90 degrees (default 25)
   * @returns true if all angles are within tolerance of 90 degrees
   */
  private validateQuadrilateralAngles(corners: CornerPoints, tolerance = 25): boolean {
    const { topLeftCorner, topRightCorner, bottomLeftCorner, bottomRightCorner } = corners;

    // Calculate angle at each corner
    const angles = [
      this.getCornerAngle(bottomLeftCorner, topLeftCorner, topRightCorner),     // top-left
      this.getCornerAngle(topLeftCorner, topRightCorner, bottomRightCorner),    // top-right
      this.getCornerAngle(topRightCorner, bottomRightCorner, bottomLeftCorner), // bottom-right
      this.getCornerAngle(bottomRightCorner, bottomLeftCorner, topLeftCorner),  // bottom-left
    ];

    // Check if all angles are within tolerance of 90 degrees
    for (const angle of angles) {
      if (Math.abs(angle - 90) > tolerance) {
        return false;
      }
    }
    return true;
  }

  /**
   * Calculate the angle at vertex b formed by points a-b-c
   */
  private getCornerAngle(a: Point, b: Point, c: Point): number {
    const v1 = { x: a.x - b.x, y: a.y - b.y };
    const v2 = { x: c.x - b.x, y: c.y - b.y };
    return angleBetweenVectors(v1, v2);
  }

  /**
   * Validates that opposite sides of the quadrilateral are similar in length.
   * This helps reject shapes that are too trapezoidal.
   * @param corners The four corner points
   * @param minRatio Minimum ratio of shorter to longer opposite sides (default 0.7)
   * @returns true if opposite sides are within the ratio threshold
   */
  private validateSideRatios(corners: CornerPoints, minRatio = 0.7): boolean {
    const { topLeftCorner, topRightCorner, bottomLeftCorner, bottomRightCorner } = corners;

    const topWidth = distance(topLeftCorner, topRightCorner);
    const bottomWidth = distance(bottomLeftCorner, bottomRightCorner);
    const leftHeight = distance(topLeftCorner, bottomLeftCorner);
    const rightHeight = distance(topRightCorner, bottomRightCorner);

    const widthRatio = Math.min(topWidth, bottomWidth) / Math.max(topWidth, bottomWidth);
    const heightRatio = Math.min(leftHeight, rightHeight) / Math.max(leftHeight, rightHeight);

    return widthRatio >= minRatio && heightRatio >= minRatio;
  }

  /**
   * Find the best quadrilateral contour from a list of contours
   */
  private findBestQuadrilateral(
    contours: any,
    cv: any,
    minArea: number,
    maxArea: number,
    frameArea: number,
    frameWidth?: number,
    frameHeight?: number
  ): any | null {
    let bestContour: any = null;
    let bestScore = 0;

    // Get frame dimensions for corner proximity scoring
    const imgWidth = frameWidth || Math.sqrt(frameArea * 1.5); // Estimate if not provided
    const imgHeight = frameHeight || Math.sqrt(frameArea / 1.5);

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

      // Get corner points for validation
      const corners = this.getCornerPoints(approx);
      if (!corners) {
        approx.delete();
        contour.delete();
        continue;
      }

      // Validate quadrilateral angles (~90° ±25°)
      if (!this.validateQuadrilateralAngles(corners)) {
        approx.delete();
        contour.delete();
        continue;
      }

      // Validate opposite side ratios (within 30% of each other)
      if (!this.validateSideRatios(corners)) {
        approx.delete();
        contour.delete();
        continue;
      }

      // KEY FILTER: Check how many corners are near frame edges
      // This is the critical difference between paper (corners near edges) and tables (floating in middle)
      const cornerMarginX = imgWidth * CORNER_EDGE_MARGIN;
      const cornerMarginY = imgHeight * CORNER_EDGE_MARGIN;

      const allCorners = [
        corners.topLeftCorner,
        corners.topRightCorner,
        corners.bottomLeftCorner,
        corners.bottomRightCorner,
      ];

      let cornersNearEdge = 0;
      for (const corner of allCorners) {
        const nearLeft = corner.x < cornerMarginX;
        const nearRight = corner.x > imgWidth - cornerMarginX;
        const nearTop = corner.y < cornerMarginY;
        const nearBottom = corner.y > imgHeight - cornerMarginY;

        // Corner is "near edge" if it's close to at least one frame edge
        if (nearLeft || nearRight || nearTop || nearBottom) {
          cornersNearEdge++;
        }
      }

      // REJECT if not enough corners are near frame edges
      // Paper being scanned will have corners near edges; tables float in the middle
      if (cornersNearEdge < MIN_CORNERS_NEAR_EDGE) {
        approx.delete();
        contour.delete();
        continue;
      }

      // Score components:
      // 1. Corner proximity score - more corners near edges = more likely to be paper
      const cornerScore = cornersNearEdge / 4;

      // 2. Area score - larger contours are preferred (paper fills more of frame than tables)
      const areaScore = area / frameArea;

      // 3. Centrality penalty - penalize contours centered in frame (tables)
      // Paper corners should be spread toward edges, not clustered in center
      const centerX = imgWidth / 2;
      const centerY = imgHeight / 2;
      const avgCornerDistFromCenter = allCorners.reduce((sum, c) => {
        return sum + Math.hypot(c.x - centerX, c.y - centerY);
      }, 0) / 4;
      const maxPossibleDist = Math.hypot(centerX, centerY);
      const spreadScore = avgCornerDistFromCenter / maxPossibleDist;

      // Combined score: heavily favor corners near edges and spread out
      const score = (cornerScore * 0.5) + (areaScore * 0.25) + (spreadScore * 0.25);

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
   * Calculate residual skew using Hough Line Transform.
   * Detects dominant horizontal lines in the corrected image.
   * @param img cv.Mat to analyze
   * @returns Skew angle in degrees (positive = clockwise tilt)
   */
  private calculateResidualSkew(img: any): number {
    const cv = getCv();
    if (!cv?.Mat) return 0;

    let gray: any = null;
    let edges: any = null;
    let lines: any = null;

    try {
      // Convert to grayscale
      gray = new cv.Mat();
      if (img.channels() === 4) {
        cv.cvtColor(img, gray, cv.COLOR_RGBA2GRAY);
      } else if (img.channels() === 3) {
        cv.cvtColor(img, gray, cv.COLOR_RGB2GRAY);
      } else {
        gray = img.clone();
      }

      // Canny edge detection
      edges = new cv.Mat();
      cv.Canny(gray, edges, 50, 150, 3);

      // Detect lines using HoughLinesP
      lines = new cv.Mat();
      cv.HoughLinesP(edges, lines, 1, Math.PI / 180, 50, 50, 10);

      if (lines.rows === 0) {
        return 0;
      }

      // Collect angles of near-horizontal lines (within 30° of horizontal)
      const angles: number[] = [];
      for (let i = 0; i < lines.rows; i++) {
        const x1 = lines.data32S[i * 4];
        const y1 = lines.data32S[i * 4 + 1];
        const x2 = lines.data32S[i * 4 + 2];
        const y2 = lines.data32S[i * 4 + 3];

        const angle = Math.atan2(y2 - y1, x2 - x1) * (180 / Math.PI);
        // Only consider near-horizontal lines (within 30° of 0° or 180°)
        if (Math.abs(angle) < 30 || Math.abs(angle) > 150) {
          // Normalize to -30 to 30 range
          const normalized = angle > 90 ? angle - 180 : (angle < -90 ? angle + 180 : angle);
          angles.push(normalized);
        }
      }

      if (angles.length === 0) {
        return 0;
      }

      // Return median angle for robustness
      angles.sort((a, b) => a - b);
      const median = angles[Math.floor(angles.length / 2)];
      return median;
    } catch {
      return 0;
    } finally {
      if (gray) gray.delete();
      if (edges) edges.delete();
      if (lines) lines.delete();
    }
  }

  /**
   * Apply rotation correction using affine transform.
   * @param img cv.Mat to rotate
   * @param angle Rotation angle in degrees (positive = counter-clockwise)
   * @returns Rotated cv.Mat (caller must delete)
   */
  private applyRotation(img: any, angle: number): any {
    const cv = getCv();
    if (!cv?.Mat) return img.clone();

    const center = new cv.Point(img.cols / 2, img.rows / 2);
    const rotationMatrix = cv.getRotationMatrix2D(center, angle, 1.0);

    const rotated = new cv.Mat();
    const dsize = new cv.Size(img.cols, img.rows);
    // Use white background (255,255,255,255) for the border
    cv.warpAffine(
      img,
      rotated,
      rotationMatrix,
      dsize,
      cv.INTER_LINEAR,
      cv.BORDER_CONSTANT,
      new cv.Scalar(255, 255, 255, 255)
    );

    rotationMatrix.delete();
    return rotated;
  }

  /**
   * Rotate image by 90, 180, or 270 degrees using cv.rotate().
   * @param img cv.Mat to rotate
   * @param degrees Rotation in degrees (90, 180, or 270)
   * @returns Rotated cv.Mat (caller must delete)
   */
  private rotateImage90(img: any, degrees: number): any {
    const cv = getCv();
    if (!cv?.Mat) return img.clone();

    const rotated = new cv.Mat();
    switch (degrees) {
      case 90:
        cv.rotate(img, rotated, cv.ROTATE_90_CLOCKWISE);
        break;
      case 180:
        cv.rotate(img, rotated, cv.ROTATE_180);
        break;
      case 270:
        cv.rotate(img, rotated, cv.ROTATE_90_COUNTERCLOCKWISE);
        break;
      default:
        return img.clone();
    }
    return rotated;
  }

  /**
   * Score how well an image orientation matches expected document characteristics.
   * Higher score = more likely correct orientation.
   * @param gray Grayscale cv.Mat
   * @param imgWidth Image width
   * @param imgHeight Image height
   * @returns Score from 0-1
   */
  private scoreOrientation(gray: any, imgWidth: number, imgHeight: number): number {
    const cv = getCv();
    if (!cv?.Mat) return 0;

    let edges: any = null;
    let sobelX: any = null;
    let sobelY: any = null;
    let magnitude: any = null;
    let angle: any = null;
    let lines: any = null;
    let topROI: any = null;
    let bottomROI: any = null;
    let topEdges: any = null;
    let bottomEdges: any = null;

    try {
      // 1. Edge Density Score (30%): top third should have more edges than bottom (headers/titles)
      const thirdHeight = Math.floor(imgHeight / 3);

      topROI = gray.roi(new cv.Rect(0, 0, imgWidth, thirdHeight));
      bottomROI = gray.roi(new cv.Rect(0, imgHeight - thirdHeight, imgWidth, thirdHeight));

      topEdges = new cv.Mat();
      bottomEdges = new cv.Mat();
      cv.Canny(topROI, topEdges, 50, 150);
      cv.Canny(bottomROI, bottomEdges, 50, 150);

      const topEdgeCount = cv.countNonZero(topEdges);
      const bottomEdgeCount = cv.countNonZero(bottomEdges);
      const totalEdges = topEdgeCount + bottomEdgeCount;
      // Documents typically have more content at top (headers, titles)
      const edgeDensityScore = totalEdges > 0 ? topEdgeCount / totalEdges : 0.5;

      // 2. Gradient Direction Score (40%): text has strong horizontal gradients
      sobelX = new cv.Mat();
      sobelY = new cv.Mat();
      cv.Sobel(gray, sobelX, cv.CV_64F, 1, 0, 3);
      cv.Sobel(gray, sobelY, cv.CV_64F, 0, 1, 3);

      magnitude = new cv.Mat();
      angle = new cv.Mat();
      cv.cartToPolar(sobelX, sobelY, magnitude, angle);

      // Count horizontal vs vertical gradients
      let horizontalGradients = 0;
      let verticalGradients = 0;
      const magThreshold = 30; // Ignore weak gradients

      for (let i = 0; i < magnitude.rows; i++) {
        for (let j = 0; j < magnitude.cols; j++) {
          const mag = magnitude.doubleAt(i, j);
          if (mag < magThreshold) continue;

          const ang = angle.doubleAt(i, j) * (180 / Math.PI);
          // Horizontal gradients: angle near 0° or 180° (from vertical edges in text)
          if (ang < 45 || ang > 135) {
            horizontalGradients++;
          } else {
            verticalGradients++;
          }
        }
      }

      const totalGradients = horizontalGradients + verticalGradients;
      // Text produces more horizontal gradients (vertical letter strokes)
      const gradientScore = totalGradients > 0 ? horizontalGradients / totalGradients : 0.5;

      // 3. Line Detection Score (30%): text lines should be horizontal
      edges = new cv.Mat();
      cv.Canny(gray, edges, 50, 150);

      lines = new cv.Mat();
      cv.HoughLinesP(edges, lines, 1, Math.PI / 180, 50, 30, 10);

      let horizontalLines = 0;
      let verticalLines = 0;

      for (let i = 0; i < lines.rows; i++) {
        const x1 = lines.data32S[i * 4];
        const y1 = lines.data32S[i * 4 + 1];
        const x2 = lines.data32S[i * 4 + 2];
        const y2 = lines.data32S[i * 4 + 3];

        const lineAngle = Math.abs(Math.atan2(y2 - y1, x2 - x1) * (180 / Math.PI));
        if (lineAngle < 20 || lineAngle > 160) {
          horizontalLines++;
        } else if (lineAngle > 70 && lineAngle < 110) {
          verticalLines++;
        }
      }

      const totalLines = horizontalLines + verticalLines;
      const lineScore = totalLines > 0 ? horizontalLines / totalLines : 0.5;

      // Combined score with weights
      const score = (edgeDensityScore * 0.3) + (gradientScore * 0.4) + (lineScore * 0.3);
      return score;
    } catch {
      return 0.5;
    } finally {
      if (edges) edges.delete();
      if (sobelX) sobelX.delete();
      if (sobelY) sobelY.delete();
      if (magnitude) magnitude.delete();
      if (angle) angle.delete();
      if (lines) lines.delete();
      if (topROI) topROI.delete();
      if (bottomROI) bottomROI.delete();
      if (topEdges) topEdges.delete();
      if (bottomEdges) bottomEdges.delete();
    }
  }

  /**
   * Detect the correct orientation of a document image.
   * Tests all 4 rotations and returns the most likely correct one.
   * @param img cv.Mat to analyze
   * @returns OrientationResult with rotation and confidence
   */
  detectOrientation(img: any): OrientationResult {
    const cv = getCv();
    if (!cv?.Mat) {
      return { rotation: 0, confidence: 0 };
    }

    let gray: any = null;
    let rotated90: any = null;
    let rotated180: any = null;
    let rotated270: any = null;
    let gray90: any = null;
    let gray180: any = null;
    let gray270: any = null;

    try {
      // Convert to grayscale once
      gray = new cv.Mat();
      if (img.channels() === 4) {
        cv.cvtColor(img, gray, cv.COLOR_RGBA2GRAY);
      } else if (img.channels() === 3) {
        cv.cvtColor(img, gray, cv.COLOR_RGB2GRAY);
      } else {
        gray = img.clone();
      }

      // Score original orientation (0°)
      const score0 = this.scoreOrientation(gray, img.cols, img.rows);

      // Score 90° rotation
      rotated90 = this.rotateImage90(img, 90);
      gray90 = new cv.Mat();
      if (rotated90.channels() === 4) {
        cv.cvtColor(rotated90, gray90, cv.COLOR_RGBA2GRAY);
      } else if (rotated90.channels() === 3) {
        cv.cvtColor(rotated90, gray90, cv.COLOR_RGB2GRAY);
      } else {
        gray90 = rotated90.clone();
      }
      const score90 = this.scoreOrientation(gray90, rotated90.cols, rotated90.rows);

      // Score 180° rotation
      rotated180 = this.rotateImage90(img, 180);
      gray180 = new cv.Mat();
      if (rotated180.channels() === 4) {
        cv.cvtColor(rotated180, gray180, cv.COLOR_RGBA2GRAY);
      } else if (rotated180.channels() === 3) {
        cv.cvtColor(rotated180, gray180, cv.COLOR_RGB2GRAY);
      } else {
        gray180 = rotated180.clone();
      }
      const score180 = this.scoreOrientation(gray180, rotated180.cols, rotated180.rows);

      // Score 270° rotation
      rotated270 = this.rotateImage90(img, 270);
      gray270 = new cv.Mat();
      if (rotated270.channels() === 4) {
        cv.cvtColor(rotated270, gray270, cv.COLOR_RGBA2GRAY);
      } else if (rotated270.channels() === 3) {
        cv.cvtColor(rotated270, gray270, cv.COLOR_RGB2GRAY);
      } else {
        gray270 = rotated270.clone();
      }
      const score270 = this.scoreOrientation(gray270, rotated270.cols, rotated270.rows);

      // Find best and second-best scores
      const scores: Array<{ rotation: 0 | 90 | 180 | 270; score: number }> = [
        { rotation: 0, score: score0 },
        { rotation: 90, score: score90 },
        { rotation: 180, score: score180 },
        { rotation: 270, score: score270 },
      ];
      scores.sort((a, b) => b.score - a.score);

      const best = scores[0];
      const secondBest = scores[1];

      // Confidence = relative difference between best and second-best
      const confidence = best.score > 0 ? (best.score - secondBest.score) / best.score : 0;

      return {
        rotation: best.rotation,
        confidence: Math.min(1, Math.max(0, confidence)),
      };
    } catch {
      return { rotation: 0, confidence: 0 };
    } finally {
      if (gray) gray.delete();
      if (rotated90) rotated90.delete();
      if (rotated180) rotated180.delete();
      if (rotated270) rotated270.delete();
      if (gray90) gray90.delete();
      if (gray180) gray180.delete();
      if (gray270) gray270.delete();
    }
  }

  /**
   * Extracts and perspective-corrects the detected paper region.
   * Calculates proper output dimensions from detected corners to avoid distortion.
   * @returns HTMLCanvasElement with the corrected image, or null if no paper detected
   */
  extractPaper(
    image: HTMLCanvasElement,
    maxWidth: number,
    maxHeight: number,
    cornerPoints?: CornerPoints
  ): ExtractPaperResult | null {
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

    // Calculate detected dimensions to determine orientation (portrait vs landscape)
    const topWidth = distance(topLeftCorner, topRightCorner);
    const bottomWidth = distance(bottomLeftCorner, bottomRightCorner);
    const leftHeight = distance(topLeftCorner, bottomLeftCorner);
    const rightHeight = distance(topRightCorner, bottomRightCorner);

    const detectedWidth = (topWidth + bottomWidth) / 2;
    const detectedHeight = (leftHeight + rightHeight) / 2;

    // Use FIXED A4 aspect ratio instead of detected ratio
    // A4 is 210mm x 297mm = 1:1.4142 (√2)
    // This prevents distortion from inaccurate corner detection
    const A4_RATIO = 1.4142; // 297/210
    const isLandscape = detectedWidth > detectedHeight;

    // Determine output dimensions using fixed A4 ratio
    let outputWidth: number;
    let outputHeight: number;

    if (isLandscape) {
      // Landscape: width > height, ratio = 1.4142
      if (maxWidth / maxHeight > A4_RATIO) {
        // Height-constrained
        outputHeight = maxHeight;
        outputWidth = Math.round(maxHeight * A4_RATIO);
      } else {
        // Width-constrained
        outputWidth = maxWidth;
        outputHeight = Math.round(maxWidth / A4_RATIO);
      }
    } else {
      // Portrait: height > width, ratio = 0.707 (1/1.4142)
      const portraitRatio = 1 / A4_RATIO;
      if (maxWidth / maxHeight > portraitRatio) {
        // Height-constrained
        outputHeight = maxHeight;
        outputWidth = Math.round(maxHeight * portraitRatio);
      } else {
        // Width-constrained
        outputWidth = maxWidth;
        outputHeight = Math.round(maxWidth / portraitRatio);
      }
    }

    // Ensure minimum dimensions
    outputWidth = Math.max(outputWidth, 100);
    outputHeight = Math.max(outputHeight, 100);

    let warpedDst = new cv.Mat();
    const dsize = new cv.Size(outputWidth, outputHeight);

    const srcTri = cv.matFromArray(4, 1, cv.CV_32FC2, [
      topLeftCorner.x, topLeftCorner.y,
      topRightCorner.x, topRightCorner.y,
      bottomLeftCorner.x, bottomLeftCorner.y,
      bottomRightCorner.x, bottomRightCorner.y,
    ]);

    const dstTri = cv.matFromArray(4, 1, cv.CV_32FC2, [
      0, 0,
      outputWidth, 0,
      0, outputHeight,
      outputWidth, outputHeight,
    ]);

    const M = cv.getPerspectiveTransform(srcTri, dstTri);
    cv.warpPerspective(img, warpedDst, M, dsize, cv.INTER_LINEAR, cv.BORDER_CONSTANT, new cv.Scalar());

    // Track corrections applied
    let appliedSkewCorrection = 0;
    let orientationCorrected = false;

    // 1. Auto-straighten small skew (0.5° - 15°)
    const residualSkew = this.calculateResidualSkew(warpedDst);
    if (Math.abs(residualSkew) > 0.5 && Math.abs(residualSkew) < 15) {
      const straightened = this.applyRotation(warpedDst, -residualSkew);
      warpedDst.delete();
      warpedDst = straightened;
      appliedSkewCorrection = residualSkew;
    }

    // 2. Detect and correct 90/180/270 degree rotation
    const orientation = this.detectOrientation(warpedDst);
    if (orientation.rotation !== 0 && orientation.confidence > 0.6) {
      const oriented = this.rotateImage90(warpedDst, orientation.rotation);
      warpedDst.delete();
      warpedDst = oriented;
      orientationCorrected = true;
    }

    cv.imshow(canvas, warpedDst);

    img.delete();
    warpedDst.delete();
    srcTri.delete();
    dstTri.delete();
    M.delete();
    if (maxContour) maxContour.delete();

    return {
      canvas,
      appliedSkewCorrection,
      detectedOrientation: orientation,
      orientationCorrected,
    };
  }

  /**
   * Rotate a canvas by a specified angle (for manual rotation).
   * @param canvas Source canvas to rotate
   * @param degrees Rotation in degrees (90, -90, or 180)
   * @returns New canvas with rotated image
   */
  rotateCanvas(canvas: HTMLCanvasElement, degrees: 90 | -90 | 180): HTMLCanvasElement {
    const cv = getCv();
    if (!cv?.Mat) {
      // Fallback: return a copy using Canvas API
      const result = document.createElement('canvas');
      const isRightAngle = degrees === 90 || degrees === -90;
      result.width = isRightAngle ? canvas.height : canvas.width;
      result.height = isRightAngle ? canvas.width : canvas.height;
      const ctx = result.getContext('2d')!;
      ctx.translate(result.width / 2, result.height / 2);
      ctx.rotate((degrees * Math.PI) / 180);
      ctx.drawImage(canvas, -canvas.width / 2, -canvas.height / 2);
      return result;
    }

    const img = cv.imread(canvas);
    const normalizedDegrees = degrees === -90 ? 270 : degrees;
    const rotated = this.rotateImage90(img, normalizedDegrees as 90 | 180 | 270);

    const resultCanvas = document.createElement('canvas');
    cv.imshow(resultCanvas, rotated);

    img.delete();
    rotated.delete();

    return resultCanvas;
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

  /**
   * Calculate blur score using Laplacian variance.
   * Higher score = sharper image, lower score = blurrier.
   * @param img cv.Mat to analyze
   * @returns Blur score (variance of Laplacian). Score < 100 is typically too blurry.
   */
  calculateBlurScore(img: any): number {
    const cv = getCv();
    if (!cv?.Mat) return 100; // Default to acceptable if OpenCV not ready

    let gray: any = null;
    let laplacian: any = null;

    try {
      gray = new cv.Mat();
      if (img.channels() === 4) {
        cv.cvtColor(img, gray, cv.COLOR_RGBA2GRAY);
      } else if (img.channels() === 3) {
        cv.cvtColor(img, gray, cv.COLOR_RGB2GRAY);
      } else {
        gray = img.clone();
      }

      laplacian = new cv.Mat();
      cv.Laplacian(gray, laplacian, cv.CV_64F);

      const mean = new cv.Mat();
      const stddev = new cv.Mat();
      cv.meanStdDev(laplacian, mean, stddev);

      const variance = stddev.data64F[0] * stddev.data64F[0];

      mean.delete();
      stddev.delete();

      return variance;
    } catch {
      return 100; // Default to acceptable on error
    } finally {
      if (gray) gray.delete();
      if (laplacian) laplacian.delete();
    }
  }

  /**
   * Calculate the skew angle of the document based on detected corners.
   * @param corners The detected corner points
   * @returns Skew angle in degrees (0 = perfectly horizontal)
   */
  calculateSkewAngle(corners: CornerPoints): number {
    const { topLeftCorner, topRightCorner, bottomLeftCorner, bottomRightCorner } = corners;

    // Calculate angle of top edge from horizontal
    const topAngle = Math.atan2(
      topRightCorner.y - topLeftCorner.y,
      topRightCorner.x - topLeftCorner.x
    ) * (180 / Math.PI);

    // Calculate angle of bottom edge from horizontal
    const bottomAngle = Math.atan2(
      bottomRightCorner.y - bottomLeftCorner.y,
      bottomRightCorner.x - bottomLeftCorner.x
    ) * (180 / Math.PI);

    // Return average absolute skew
    return (Math.abs(topAngle) + Math.abs(bottomAngle)) / 2;
  }

  /**
   * Calculate glare percentage by detecting overexposed regions.
   * @param img cv.Mat to analyze
   * @param corners Optional corner points to limit analysis to document region
   * @returns Percentage of pixels that are overexposed (> 240 brightness)
   */
  calculateGlareScore(img: any, corners?: CornerPoints): number {
    const cv = getCv();
    if (!cv?.Mat) return 0;

    let gray: any = null;
    let mask: any = null;

    try {
      gray = new cv.Mat();
      if (img.channels() === 4) {
        cv.cvtColor(img, gray, cv.COLOR_RGBA2GRAY);
      } else if (img.channels() === 3) {
        cv.cvtColor(img, gray, cv.COLOR_RGB2GRAY);
      } else {
        gray = img.clone();
      }

      // If corners provided, create a mask for the document region
      let totalPixels: number;
      let overexposedPixels: number;

      if (corners) {
        mask = cv.Mat.zeros(gray.rows, gray.cols, cv.CV_8U);
        const points = [
          corners.topLeftCorner,
          corners.topRightCorner,
          corners.bottomRightCorner,
          corners.bottomLeftCorner,
        ];
        const contour = cv.matFromArray(4, 1, cv.CV_32SC2,
          points.flatMap(p => [Math.round(p.x), Math.round(p.y)])
        );
        const contours = new cv.MatVector();
        contours.push_back(contour);
        cv.drawContours(mask, contours, 0, new cv.Scalar(255), -1);

        // Count pixels in document region
        totalPixels = cv.countNonZero(mask);

        // Apply mask and count overexposed
        const masked = new cv.Mat();
        cv.bitwise_and(gray, mask, masked);
        const thresh = new cv.Mat();
        cv.threshold(masked, thresh, 240, 255, cv.THRESH_BINARY);
        const overexposed = new cv.Mat();
        cv.bitwise_and(thresh, mask, overexposed);
        overexposedPixels = cv.countNonZero(overexposed);

        contour.delete();
        contours.delete();
        masked.delete();
        thresh.delete();
        overexposed.delete();
      } else {
        totalPixels = gray.rows * gray.cols;
        const thresh = new cv.Mat();
        cv.threshold(gray, thresh, 240, 255, cv.THRESH_BINARY);
        overexposedPixels = cv.countNonZero(thresh);
        thresh.delete();
      }

      return totalPixels > 0 ? (overexposedPixels / totalPixels) * 100 : 0;
    } catch {
      return 0;
    } finally {
      if (gray) gray.delete();
      if (mask) mask.delete();
    }
  }

  /**
   * Check if all corners are within the frame with a margin.
   * @param corners The detected corner points
   * @param frameWidth Frame width in pixels
   * @param frameHeight Frame height in pixels
   * @param margin Minimum distance from edge (default 10px)
   * @returns true if all corners are safely within frame
   */
  checkCompleteness(
    corners: CornerPoints,
    frameWidth: number,
    frameHeight: number,
    margin = 10
  ): boolean {
    const points = [
      corners.topLeftCorner,
      corners.topRightCorner,
      corners.bottomLeftCorner,
      corners.bottomRightCorner,
    ];

    for (const p of points) {
      if (p.x < margin || p.x > frameWidth - margin ||
          p.y < margin || p.y > frameHeight - margin) {
        return false;
      }
    }
    return true;
  }

  /**
   * Calculate document coverage as percentage of frame.
   * @param corners The detected corner points
   * @param frameWidth Frame width
   * @param frameHeight Frame height
   * @returns Coverage percentage (0-100)
   */
  calculateDocumentCoverage(
    corners: CornerPoints,
    frameWidth: number,
    frameHeight: number
  ): number {
    const { topLeftCorner, topRightCorner, bottomLeftCorner, bottomRightCorner } = corners;

    // Calculate document area using Shoelace formula
    const docArea = 0.5 * Math.abs(
      (topLeftCorner.x * topRightCorner.y - topRightCorner.x * topLeftCorner.y) +
      (topRightCorner.x * bottomRightCorner.y - bottomRightCorner.x * topRightCorner.y) +
      (bottomRightCorner.x * bottomLeftCorner.y - bottomLeftCorner.x * bottomRightCorner.y) +
      (bottomLeftCorner.x * topLeftCorner.y - topLeftCorner.x * bottomLeftCorner.y)
    );

    const frameArea = frameWidth * frameHeight;
    return (docArea / frameArea) * 100;
  }

  /**
   * Highlights the detected paper in the image with a colored overlay.
   * @param image Source image (HTMLCanvasElement, HTMLImageElement, etc.)
   * @param options { color: string, thickness: number }
   * @returns HTMLCanvasElement with highlighted paper, or null if no paper detected
   */
  highlightPaper(
    image: HTMLCanvasElement | HTMLImageElement,
    options: { color?: string; thickness?: number } = {}
  ): HTMLCanvasElement | null {
    const cv = getCv();
    if (!cv?.Mat) return null;

    const canvas = document.createElement('canvas');
    const img = cv.imread(image);

    canvas.width = img.cols;
    canvas.height = img.rows;

    const contour = this.findPaperContour(img);
    if (!contour) {
      img.delete();
      return null;
    }

    const color = options.color || '#00FF00';
    const thickness = options.thickness || 3;

    // Parse hex color to BGR
    const r = parseInt(color.slice(1, 3), 16);
    const g = parseInt(color.slice(3, 5), 16);
    const b = parseInt(color.slice(5, 7), 16);

    // Draw the contour on the image
    const contours = new cv.MatVector();
    contours.push_back(contour);
    cv.drawContours(img, contours, 0, new cv.Scalar(b, g, r, 255), thickness);

    cv.imshow(canvas, img);

    img.delete();
    contour.delete();
    contours.delete();

    return canvas;
  }

  /**
   * Perform comprehensive quality check on detected document.
   * @param img cv.Mat of the current frame
   * @param corners Detected corner points
   * @param frameWidth Frame width
   * @param frameHeight Frame height
   * @returns Quality result with warnings
   */
  checkQuality(
    img: any,
    corners: CornerPoints,
    frameWidth: number,
    frameHeight: number
  ): QualityResult {
    const warnings: QualityWarning[] = [];

    // Calculate all quality metrics
    const blurScore = this.calculateBlurScore(img);
    const skewAngle = this.calculateSkewAngle(corners);
    const glarePercentage = this.calculateGlareScore(img, corners);
    const isComplete = this.checkCompleteness(corners, frameWidth, frameHeight);
    const documentCoverage = this.calculateDocumentCoverage(corners, frameWidth, frameHeight);

    // Check blur (score < 100 is too blurry)
    if (blurScore < 100) {
      warnings.push({
        type: 'blur',
        message: 'scanner.holdSteady',
        severity: blurScore < 50 ? 'error' : 'warning',
      });
    }

    // Check skew (> 15° is too tilted)
    if (skewAngle > 15) {
      warnings.push({
        type: 'skew',
        message: 'scanner.straightenDocument',
        severity: skewAngle > 25 ? 'error' : 'warning',
      });
    }

    // Check glare (> 5% overexposed is problematic)
    if (glarePercentage > 5) {
      warnings.push({
        type: 'glare',
        message: 'scanner.avoidGlare',
        severity: glarePercentage > 15 ? 'error' : 'warning',
      });
    }

    // Check completeness
    if (!isComplete) {
      warnings.push({
        type: 'incomplete',
        message: 'scanner.alignWithGuides',
        severity: 'warning',
      });
    }

    // Check document size (< 20% of frame is too small)
    if (documentCoverage < 20) {
      warnings.push({
        type: 'tooSmall',
        message: 'scanner.moveCloser',
        severity: 'warning',
      });
    }

    // Document is acceptable if there are no error-level warnings
    const hasErrors = warnings.some(w => w.severity === 'error');

    return {
      isAcceptable: !hasErrors,
      warnings,
      blurScore,
      skewAngle,
      glarePercentage,
      documentCoverage,
    };
  }
}
