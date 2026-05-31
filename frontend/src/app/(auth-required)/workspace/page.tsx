"use client"

// pages/workspace.tsx
import { useState, useEffect } from "react"
import { HistorySidebar, HistoryItem } from "@/components/history-sidebar"
import { LiveWorkingArea } from "@/components/live-working-area"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"

export default function WorkspacePage() {
  const [history, setHistory] = useState<HistoryItem[]>([])
  const [selectedIdea, setSelectedIdea] = useState<HistoryItem | null>(null)
  const [activeAgent, setActiveAgent] = useState<string | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)
  const [productData, setProductData] = useState<any>(null)
  const [customerData, setCustomerData] = useState<any>(null)
  const [riskData, setRiskData] = useState<any>(null)
  const [engineerData, setEngineerData] = useState<any>(null)
  const [diagramUrl, setDiagramUrl] = useState<string | null>(null)
  const [summaryData, setSummaryData] = useState<any>(null)
  const [classification, setClassification] = useState<any>(null)
  const [chatHistory, setChatHistory] = useState<any[]>([])
  const [workflowStep, setWorkflowStep] = useState<"input" | "classifying" | "clarifying" | "product" | "customer" | "risk" | "engineer" | "diagram" | "summary" | "review" | "next">("input")
  const [apiKey, setApiKey] = useState("")
  const [apiKeyInput, setApiKeyInput] = useState("")
  const [showApiKey, setShowApiKey] = useState(false)

  useEffect(() => {
    console.log("WorkspacePage mounted, fetching projects...")
    fetchProjects()
  }, [])

  useEffect(() => {
    const storedKey = localStorage.getItem("user_api_key")
    if (storedKey) {
      setApiKey(storedKey)
      setApiKeyInput(storedKey)
    }
  }, [])

  const handleSaveApiKey = () => {
    const trimmedKey = apiKeyInput.trim()
    if (trimmedKey) {
      localStorage.setItem("user_api_key", trimmedKey)
      setApiKey(trimmedKey)
    } else {
      localStorage.removeItem("user_api_key")
      setApiKey("")
    }
  }

  const handleClearApiKey = () => {
    setApiKey("")
    setApiKeyInput("")
    localStorage.removeItem("user_api_key")
  }

  const buildProxyHeaders = (projectId?: string) => {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    }
    if (projectId) {
      headers["X-Project-Id"] = projectId
    }
    if (apiKey) {
      headers["X-User-Api-Key"] = apiKey
    }
    return headers
  }

  const fetchProjects = async () => {
    try {
      const response = await fetch("/api/projects")
      if (response.ok) {
        const data = await response.json()
        const formattedHistory: HistoryItem[] = data.map((project: any) => ({
          id: project.id,
          title: project.title,
          timestamp: new Date(project.updatedAt),
          status: project.status === "COMPLETED" ? "completed" : "in-progress"
        }))
        setHistory(formattedHistory)
      }
    } catch (error) {
      console.error("Error fetching projects:", error)
    }
  }

  const handleNewProject = () => {
    setSelectedIdea(null)
    setActiveAgent(null)
    setChatHistory([])
    setProductData(null)
    setCustomerData(null)
    setRiskData(null)
    setEngineerData(null)
    setDiagramUrl(null)
    setSummaryData(null)
    setClassification(null)
    setWorkflowStep("input")
  }

  const handleIdeaSubmit = async (ideaTitle: string) => {
    setIsGenerating(true)
    setActiveAgent(null)
    setWorkflowStep("classifying")

    try {
      // 1. Create Project in DB
      const projectRes = await fetch("/api/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: ideaTitle }),
      })

      if (!projectRes.ok) throw new Error("Failed to create project")
      
      const project = await projectRes.json()
      
      const newIdea: HistoryItem = {
        id: project.id,
        title: project.title,
        timestamp: new Date(project.createdAt),
        status: "in-progress"
      }
      
      setHistory(prev => [newIdea, ...prev])
      setSelectedIdea(newIdea)

      // 2. Classify
      const classifyRes = await fetch("/api/proxy/classify", {
          method: "POST",
          headers: {
            ...buildProxyHeaders(project.id),
          },
          body: JSON.stringify({ idea: ideaTitle }),
      })
      
      if (classifyRes.ok) {
          const classifyData = await classifyRes.json()
          setClassification(classifyData)
      }

      // 3. Run Clarifier
      const clarifierRes = await fetch("/api/proxy/clarify", {
          method: "POST",
          headers: {
            ...buildProxyHeaders(project.id),
          },
          body: JSON.stringify({ 
              messages: [{ role: "user", content: `I have a new product idea: ${ideaTitle}. Please help me refine it.` }] 
          }),
      })

      if (clarifierRes.ok) {
          const clarifierData = await clarifierRes.json()
          setChatHistory([
              { role: "user", content: ideaTitle },
              { role: "assistant", content: clarifierData.parsed || clarifierData.response }
          ])
          setActiveAgent("clarifier")
          setWorkflowStep("clarifying") 
      }

    } catch (error) {
      console.error("Error generating product:", error)
    } finally {
      setIsGenerating(false)
    }
  }

  const safeParseJSON = (content: any) => {
    if (typeof content === 'string') {
      try {
        return JSON.parse(content)
      } catch (e) {
        console.error("Failed to parse JSON content:", content)
        return null
      }
    }
    return content
  }

  const handleSelectIdea = async (idea: HistoryItem) => {
    setSelectedIdea(idea)
    setActiveAgent(null)
    setChatHistory([])
    setProductData(null)
    setCustomerData(null)
    setRiskData(null)
    setEngineerData(null)
    setDiagramUrl(null)
    setSummaryData(null)
    setClassification(null)
    setWorkflowStep("input")

    try {
        const response = await fetch(`/api/projects/${idea.id}`)
        if (response.ok) {
            const project = await response.json()
            if (project.responses) {
                // Load all agent responses
                const productResponse = project.responses.find((r: any) => r.agentType === "PRODUCT")
                if (productResponse) setProductData(safeParseJSON(productResponse.content))

                const customerResponse = project.responses.find((r: any) => r.agentType === "CUSTOMER")
                if (customerResponse) setCustomerData(safeParseJSON(customerResponse.content))

                const riskResponse = project.responses.find((r: any) => r.agentType === "RISK")
                if (riskResponse) setRiskData(safeParseJSON(riskResponse.content))

                const engineerResponse = project.responses.find((r: any) => r.agentType === "ENGINEER")
                if (engineerResponse) setEngineerData(safeParseJSON(engineerResponse.content))

                const summaryResponse = project.responses.find((r: any) => r.agentType === "SUMMARY")
                if (summaryResponse) setSummaryData(safeParseJSON(summaryResponse.content))
                
                const classifierResponse = project.responses.find((r: any) => r.agentType === "CLASSIFIER")
                if (classifierResponse) setClassification(safeParseJSON(classifierResponse.content))

                const clarifierResponse = project.responses.find((r: any) => r.agentType === "CLARIFIER")
                if (clarifierResponse) {
                    const parsed = safeParseJSON(clarifierResponse.content)
                    if (parsed && parsed.response) {
                         setChatHistory([
                            { role: "user", content: project.title },
                            { role: "assistant", content: parsed }
                        ])
                    }
                }

                const diagramResponse = project.responses.find((r: any) => r.agentType === "DIAGRAM")
                if (diagramResponse) {
                    const parsed = safeParseJSON(diagramResponse.content)
                    if (parsed && parsed.diagram_url) {
                        setDiagramUrl(parsed.diagram_url)
                    }
                }

                // Determine latest state
                if (summaryResponse) {
                    setActiveAgent("summary")
                    setWorkflowStep("summary")
                } else if (diagramResponse) {
                    setActiveAgent("diagram")
                    setWorkflowStep("summary")
                } else if (engineerResponse) {
                    setActiveAgent("engineer")
                    setWorkflowStep("diagram")
                } else if (riskResponse) {
                    setActiveAgent("risk")
                    setWorkflowStep("engineer")
                } else if (customerResponse) {
                    setActiveAgent("customer")
                    setWorkflowStep("risk")
                } else if (productResponse) {
                    setActiveAgent("product")
                    setWorkflowStep("customer")
                } else if (clarifierResponse) {
                    setActiveAgent("clarifier")
                    setWorkflowStep("clarifying")
                }
            }
        }
    } catch (error) {
        console.error("Error fetching project details:", error)
    }
  }

  const handleContinueWorkflow = async () => {
      if (!selectedIdea) return
      setIsGenerating(true)

      try {
          if (activeAgent === "clarifier" || !activeAgent) {
             // Move to Product
             setActiveAgent("product")
             setWorkflowStep("product")
             
             // We need requirements from chat history for product agent
             // Simple concatenation of user messages for now
             const requirements = chatHistory
                .filter(m => m.role === 'user')
                .map(m => m.content)
                .join("\n")

             const response = await fetch("/api/proxy/generate_product", {
                 method: "POST",
                 headers: buildProxyHeaders(selectedIdea.id),
                 body: JSON.stringify({ requirements })
             })
             const data = await response.json()
             setProductData(data)
             if (data.diagram_url) setDiagramUrl(data.diagram_url)
             
          } else if (activeAgent === "product") {
              // Move to Customer
              setActiveAgent("customer")
              setWorkflowStep("customer")
              
              const response = await fetch("/api/proxy/generate_customer", {
                  method: "POST",
                  headers: buildProxyHeaders(selectedIdea.id),
                  body: JSON.stringify({ product_data: productData.product_data })
              })
              const data = await response.json()
              setCustomerData(data)

          } else if (activeAgent === "customer") {
              // Move to Risk
              setActiveAgent("risk")
              setWorkflowStep("risk")
              
              // Passing customer data as engineer data for now to satisfy API
              const response = await fetch("/api/proxy/generate_risk", {
                  method: "POST",
                  headers: buildProxyHeaders(selectedIdea.id),
                  body: JSON.stringify({ engineer_data: customerData.customer_data }) 
              })
              const data = await response.json()
              setRiskData(data)

          } else if (activeAgent === "risk") {
              // Move to Engineer
              setActiveAgent("engineer")
              setWorkflowStep("engineer")

              const response = await fetch("/api/proxy/generate_engineer", {
                  method: "POST",
                  headers: buildProxyHeaders(selectedIdea.id),
                  body: JSON.stringify({ customer_data: customerData.customer_data })
              })
              const data = await response.json()
              setEngineerData(data)

          } else if (activeAgent === "engineer") {
              // Move to Diagram
              setActiveAgent("diagram")
              setWorkflowStep("diagram")

              const response = await fetch("/api/proxy/generate_diagram", {
                  method: "POST",
                  headers: buildProxyHeaders(selectedIdea.id),
                  body: JSON.stringify({ 
                      project_summary: { ...productData?.product_data, ...engineerData?.engineer_data, title: selectedIdea.title }
                  })
              })
              const data = await response.json()
              if (data.diagram_url) {
                  setDiagramUrl(data.diagram_url)
              }

          } else if (activeAgent === "diagram") {
              // Move to Summary - generate final summary
              setActiveAgent("summary")
              setWorkflowStep("summary")

              const response = await fetch("/api/proxy/generate_summary", {
                  method: "POST",
                  headers: buildProxyHeaders(selectedIdea.id),
                  body: JSON.stringify({ 
                      final_data: {
                          product_data: productData?.product_data,
                          customer_data: customerData?.customer_data,
                          risk_data: riskData?.risk_data,
                          engineer_data: engineerData?.engineer_data
                      }
                  })
              })
              const summaryResult = await response.json()
              setSummaryData(summaryResult)

              // Mark project as completed
              await fetch(`/api/projects/${selectedIdea.id}`, {
                  method: "PATCH",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ status: "COMPLETED" })
              })

              // Update local history state
              setHistory(prev => prev.map(item => 
                  item.id === selectedIdea.id 
                      ? { ...item, status: "completed" } 
                      : item
              ))
          }
      } catch (error) {
          console.error("Error in workflow:", error)
      } finally {
          setIsGenerating(false)
      }
  }

  const handleAgentMessage = async (message: string) => {
    const newHistory = [...chatHistory, { role: "user", content: message }]
    setChatHistory(newHistory)
    
    if (activeAgent === "clarifier" && selectedIdea?.id) {
        try {
            // Sanitize history to ensure content is always a string for the API
            const sanitizedHistory = newHistory.map(msg => ({
                ...msg,
                content: typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content)
            }))

            const response = await fetch("/api/proxy/clarify", {
                method: "POST",
                headers: buildProxyHeaders(selectedIdea.id),
                body: JSON.stringify({ messages: sanitizedHistory })
            })
            const data = await response.json()
            if (data.response) {
                setChatHistory(prev => [...prev, { role: "assistant", content: data.parsed || data.response }])
            }
        } catch (error) {
            console.error("Error in chat:", error)
        }
    }
  }

  const handleAgentSelect = (agentId: string) => {
    setActiveAgent(agentId)
  }

  const handleDeleteProject = async (id: string) => {
    if (!confirm("Are you sure you want to delete this project?")) return

    try {
      const response = await fetch(`/api/projects/${id}`, {
        method: "DELETE",
      })

      if (response.ok) {
        setHistory(prev => prev.filter(item => item.id !== id))
        if (selectedIdea?.id === id) {
          handleNewProject()
        }
      } else {
        console.error("Failed to delete project")
      }
    } catch (error) {
      console.error("Error deleting project:", error)
    }
  }

  const handleRegenerate = async () => {
      if (!selectedIdea || !activeAgent) return
      setIsGenerating(true)

      try {
          if (activeAgent === "product") {
             const requirements = chatHistory
                .filter(m => m.role === 'user')
                .map(m => m.content)
                .join("\n")

             const response = await fetch("/api/proxy/generate_product", {
                 method: "POST",
                 headers: buildProxyHeaders(selectedIdea.id),
                 body: JSON.stringify({ requirements })
             })
             const data = await response.json()
             setProductData(data)
             if (data.diagram_url) setDiagramUrl(data.diagram_url)
             
          } else if (activeAgent === "customer") {
              const response = await fetch("/api/proxy/generate_customer", {
                  method: "POST",
                  headers: buildProxyHeaders(selectedIdea.id),
                  body: JSON.stringify({ product_data: productData.product_data })
              })
              const data = await response.json()
              setCustomerData(data)

          } else if (activeAgent === "risk") {
              // Passing customer data as engineer data for now to satisfy API
              const response = await fetch("/api/proxy/generate_risk", {
                  method: "POST",
                  headers: buildProxyHeaders(selectedIdea.id),
                  body: JSON.stringify({ engineer_data: customerData.customer_data }) 
              })
              const data = await response.json()
              setRiskData(data)

          } else if (activeAgent === "engineer") {
              const response = await fetch("/api/proxy/generate_engineer", {
                  method: "POST",
                  headers: buildProxyHeaders(selectedIdea.id),
                  body: JSON.stringify({ customer_data: customerData.customer_data })
              })
              const data = await response.json()
              setEngineerData(data)

          } else if (activeAgent === "summary") {
              const response = await fetch("/api/proxy/generate_summary", {
                  method: "POST",
                  headers: buildProxyHeaders(selectedIdea.id),
                  body: JSON.stringify({ 
                      final_data: {
                          product_data: productData?.product_data,
                          customer_data: customerData?.customer_data,
                          risk_data: riskData?.risk_data,
                          engineer_data: engineerData?.engineer_data
                      }
                  })
              })
              const summaryResult = await response.json()
              setSummaryData(summaryResult)

          } else if (activeAgent === "diagram") {
              const response = await fetch("/api/proxy/generate_diagram", {
                  method: "POST",
                  headers: buildProxyHeaders(selectedIdea.id),
                  body: JSON.stringify({ 
                      project_summary: productData?.product_data || summaryData || { title: selectedIdea.title }
                  })
              })
              const data = await response.json()
              if (data.diagram_url) {
                  setDiagramUrl(data.diagram_url)
              }
          }
      } catch (error) {
          console.error("Error regenerating:", error)
      } finally {
          setIsGenerating(false)
      }
  }

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <div className="w-80 border-r border-border/50 flex-shrink-0">
        <HistorySidebar 
          history={history} 
          onSelectIdea={handleSelectIdea} 
          onNewProject={handleNewProject}
          onDeleteProject={handleDeleteProject}
        />
      </div>
      
      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Top Bar */}
        <div className="h-16 border-b border-border/50 flex items-center px-6">
          <h1 className="text-xl font-semibold">Product Idea Workspace</h1>
          <div className="ml-auto flex items-center space-x-4">
            <div className="flex items-center gap-2">
              <label htmlFor="user-api-key" className="text-xs text-muted-foreground">
                API Key
              </label>
              <Input
                id="user-api-key"
                type={showApiKey ? "text" : "password"}
                placeholder="sk-..."
                value={apiKeyInput}
                onChange={(e) => setApiKeyInput(e.target.value)}
                className="h-8 w-56 text-xs"
              />
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowApiKey((prev) => !prev)}
                className="h-8 text-xs"
              >
                {showApiKey ? "Hide" : "Show"}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleSaveApiKey}
                disabled={apiKeyInput.trim() === apiKey}
                className="h-8 text-xs"
              >
                Save
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleClearApiKey}
                disabled={!apiKeyInput && !apiKey}
                className="h-8 text-xs"
              >
                Clear
              </Button>
            </div>
            <span className="text-[10px] text-muted-foreground">
              Stored locally in your browser.
            </span>
            <div className="text-sm text-muted-foreground">
              {selectedIdea ? `Working on: ${selectedIdea.title}` : "No idea selected"}
            </div>
            {selectedIdea && (
              <div className="flex items-center space-x-2">
                {["clarifier", "product", "customer", "risk", "engineer", "diagram", "summary"].map(agent => (
                    <button 
                      key={agent}
                      onClick={() => handleAgentSelect(agent)}
                      className={`px-3 py-1 rounded-full text-xs font-medium capitalize ${
                        activeAgent === agent 
                          ? "bg-accent text-accent-foreground" 
                          : "bg-accent/10 text-accent hover:bg-accent/20"
                      }`}
                    >
                      {agent}
                    </button>
                ))}
              </div>
            )}
          </div>
        </div>
        
        {/* Working Area */}
        <div className="flex-1 p-6 overflow-auto">
          <LiveWorkingArea 
            activeAgent={activeAgent}
            currentIdea={selectedIdea?.title || ""}
            onIdeaSubmit={handleIdeaSubmit}
            onAgentMessage={handleAgentMessage}
            isGenerating={isGenerating}
            productData={productData}
            customerData={customerData}
            riskData={riskData}
            engineerData={engineerData}
            diagramUrl={diagramUrl}
            summaryData={summaryData}
            chatHistory={chatHistory}
            classification={classification}
            workflowStep={workflowStep}
            onContinue={handleContinueWorkflow}
            onRegenerate={handleRegenerate}
          />
        </div>
      </div>
    </div>
  )
}