import { Box, Button, Stack, TextField, Typography } from "@mui/material";
import { useState, useEffect } from "react";
import ReactMarkdown from "react-markdown"

export default function Home() {

  // const host = process.env.REACT_API_URL;
  const host = "http://127.0.0.1:5000"

  const [availableProfessors, setAvailableProfessors] = useState([])
  const getAvailableProfessors = async () => {
    const response = await fetch(`${host}/professors`)
    const professors = await response.json()
    setAvailableProfessors(professors['professors'])
  }
  useEffect(() => {
    getAvailableProfessors()
  }, [])

  const [selectedProfessor, setSelectedProfessor] = useState(null)
  const [messages, setMessages] = useState([]);
  useEffect(() => {
    setMessages([
      {
        role: 'assistant',
        content: `How can I help you learn about ${selectedProfessor}?`
      }
    ])
  }, [selectedProfessor])

  const [message, setMessage] = useState('');

  const sendMessage = async () => {
    if (!message)
      return;
    setMessage('');
    const newMessages = [...messages, { role: 'user', content: message }, { role: 'assistant', content: '' }]
    setMessages(newMessages);
    try {
      const body = {
        professor: selectedProfessor,
        history: newMessages.slice(0, -1), // List of objects
      };
    
      const response = await fetch(`${host}/chat_with_professor`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      });
    
      // Check if the response body exists for streaming
      if (!response.body) {
        throw new Error('No response body');
      }
    
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let done = false;
      let message = '';  // Accumulate the message chunks here
    
      while (!done) {
        const { value, done: streamDone } = await reader.read();
        done = streamDone;
        message += decoder.decode(value, { stream: !done });  // Append chunk to message
    
        setMessages((messages) => {
          let updatedMessages = [...messages];
          updatedMessages[updatedMessages.length - 1].content = message;
          return updatedMessages;
        });
      }
    }
    catch (error) {
      console.error('Error fetching data:', error);
    }
    

  }


  return (
    <Box width="100vw" height="100vh" display="flex" justifyContent="center" alignItems="center" flexDirection="column" overflow="hidden">
      <Stack direction="row">
        {availableProfessors.map(prof => (
          <Button variant={prof === selectedProfessor ? 'contained' : 'outlined'} onClick={() => {setSelectedProfessor(selectedProfessor === prof ? null : prof)}}>{prof}</Button>
        ))}
      </Stack>
      <Box width="60vw" borderRadius={2} textAlign="center" p={2}>
        <Typography variant="h4">Professor Chatbot</Typography>
      </Box>

      {
        selectedProfessor ?
          (<Box width="100vw" display="flex" flexDirection="column" justifyContent="center" alignItems="center">
            <Stack direction="column" width="60vw" height="75vh" border="1px solid #ccc" spacing={2} borderRadius={2} overflow="hidden">
              <Stack direction="column" spacing={2} flexGrow={1} overflow="auto" maxHeight="100%" pr={1}> {/* Adds padding to prevent scrollbar overlap */}
                {messages.map((message, index) => {
                  const text = message.role === "assistant" ? <ReactMarkdown>{message.content}</ReactMarkdown> : message.content
                  return (
                    <Box
                      key={index}
                      display="flex"
                      justifyContent={message.role === 'assistant' ? 'flex-start' : 'flex-end'}
                      p={1}
                    >
                      <Box
                        p={2}
                        borderRadius={16}
                        bgcolor={message.role === 'assistant' ? 'rgba(184, 188, 188, 0.64)' : '#66adff'}
                        boxShadow="0px 3px 6px rgba(0, 0, 0, 0.1)"
                        maxWidth="70%"
                      >
                        <Typography color="#0b1215">{text}</Typography>
                      </Box>
                    </Box>
                  )
                })}
              </Stack>

              <Stack direction="row" spacing={2} mt={1}>
                <TextField
                  label="Type your message..."
                  fullWidth
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault()
                      sendMessage()
                    }
                  }}
                  variant="outlined"
                  sx={{
                    bgcolor: "white",
                    borderRadius: 1,
                    boxShadow: "0px 2px 4px rgba(0, 0, 100, 0.1)",
                  }}
                />
                <Button
                  variant="contained"
                  onClick={sendMessage}
                  sx={{
                    bgcolor: "#447bc9",
                    color: "white",
                    borderRadius: 1,
                    boxShadow: "0px 2px 4px rgba(0, 0, 0, 0.2)",
                    "&:hover": {
                      bgcolor: "#3568a5",
                    },
                  }}
                >
                  Send
                </Button>
              </Stack>
            </Stack>
          </Box>)
          :
          <Typography>Please select a professor</Typography>
      }
    </Box>
  )
}