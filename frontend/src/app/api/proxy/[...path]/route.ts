import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/app/api/auth/[...nextauth]/route";

import { createAgentResponse } from "@/lib/db";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

// Map URL paths to AgentType enum
const PATH_TO_AGENT_TYPE: Record<string, string> = {
    "generate_product": "PRODUCT",
    "classify": "CLASSIFIER",
    "clarify": "CLARIFIER",
    "generate_customer": "CUSTOMER",
    "generate_risk": "RISK",
    "generate_engineer": "ENGINEER",
    "generate_diagram": "DIAGRAM",
    "generate_summary": "SUMMARY"
};

async function proxyRequest(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
    const session = await getServerSession(authOptions);

    if (!session) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { path: pathParams } = await params;
    const path = pathParams.join("/");
    const url = `${BACKEND_URL}/${path}`;
    const projectId = req.headers.get("X-Project-Id");

    try {
        const body = req.method !== "GET" ? await req.text() : undefined;

        const headers: HeadersInit = {
            "Content-Type": "application/json",
        };

        const userApiKey = req.headers.get("X-User-Api-Key");
        if (userApiKey) {
            headers["X-User-Api-Key"] = userApiKey;
        }

        // Forward specific headers if needed, e.g., Authorization if backend needs it
        // headers['Authorization'] = req.headers.get('Authorization') || '';

        const response = await fetch(url, {
            method: req.method,
            headers: headers,
            body: body,
        });

        const data = await response.json();

        // Store response if we have a project ID and it's a valid agent path
        if (response.ok && projectId) {
            const lastPathSegment = pathParams[pathParams.length - 1];
            const agentType = PATH_TO_AGENT_TYPE[lastPathSegment];

            if (agentType) {
                // Store asynchronously without blocking the response
                createAgentResponse(projectId, agentType, data)
                    .catch(err => console.error("Failed to store agent response:", err));
            }
        }

        return NextResponse.json(data, { status: response.status });
    } catch (error) {
        console.error("Proxy error:", error);
        return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
    }
}

export async function GET(req: NextRequest, context: { params: Promise<{ path: string[] }> }) {
    return proxyRequest(req, context);
}

export async function POST(req: NextRequest, context: { params: Promise<{ path: string[] }> }) {
    return proxyRequest(req, context);
}

export async function PUT(req: NextRequest, context: { params: Promise<{ path: string[] }> }) {
    return proxyRequest(req, context);
}

export async function DELETE(req: NextRequest, context: { params: Promise<{ path: string[] }> }) {
    return proxyRequest(req, context);
}
