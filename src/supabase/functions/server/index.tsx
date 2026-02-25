import { Hono } from "npm:hono";
import { cors } from "npm:hono/cors";
import { logger } from "npm:hono/logger";
import { createClient } from "jsr:@supabase/supabase-js@2";
import * as kv from "./kv_store.tsx";

const app = new Hono();

// Create Supabase client
const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
const supabaseServiceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const supabaseAnonKey = Deno.env.get("SUPABASE_ANON_KEY")!;

// Enable logger
app.use('*', logger(console.log));

// Enable CORS for all routes and methods
app.use(
  "/*",
  cors({
    origin: "*",
    allowHeaders: ["Content-Type", "Authorization"],
    allowMethods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    exposeHeaders: ["Content-Length"],
    maxAge: 600,
  }),
);

// Middleware to verify user authentication
async function verifyAuth(authHeader: string | null) {
  if (!authHeader || !authHeader.startsWith("Bearer ")) {
    return null;
  }
  
  const token = authHeader.split(" ")[1];
  const supabase = createClient(supabaseUrl, supabaseAnonKey);
  
  const { data: { user }, error } = await supabase.auth.getUser(token);
  
  if (error || !user) {
    console.log("Auth verification error:", error);
    return null;
  }
  
  return user;
}

// Health check endpoint
app.get("/make-server-f876292a/health", (c) => {
  return c.json({ status: "ok" });
});

// Sign up endpoint
app.post("/make-server-f876292a/signup", async (c) => {
  try {
    const { email, password, name } = await c.req.json();
    
    if (!email || !password) {
      return c.json({ error: "Email and password required" }, 400);
    }

    const supabase = createClient(supabaseUrl, supabaseServiceKey);
    
    const { data, error } = await supabase.auth.admin.createUser({
      email,
      password,
      user_metadata: { name },
      // Automatically confirm the user's email since an email server hasn't been configured.
      email_confirm: true
    });

    if (error) {
      console.log("Signup error:", error);
      return c.json({ error: error.message }, 400);
    }

    return c.json({ user: data.user });
  } catch (error) {
    console.log("Signup exception:", error);
    return c.json({ error: "Internal server error during signup" }, 500);
  }
});

// Create conversation
app.post("/make-server-f876292a/conversations", async (c) => {
  try {
    const user = await verifyAuth(c.req.header("Authorization"));
    if (!user) {
      return c.json({ error: "Unauthorized" }, 401);
    }

    const { title } = await c.req.json();
    
    // Check existing conversations count
    const userConversationsKey = `conversations:${user.id}`;
    const existingConversations = await kv.get(userConversationsKey) || [];
    
    if (existingConversations.length >= 3) {
      return c.json({ error: "대화방은 최대 3개까지 생성할 수 있습니다." }, 400);
    }

    const conversationId = crypto.randomUUID();
    const now = new Date().toISOString();

    const conversation = {
      id: conversationId,
      userId: user.id,
      title: title || "새로운 대화",
      createdAt: now,
      updatedAt: now,
      messages: [], // 메시지 리스트 초기화
    };

    console.log("Creating conversation:", conversationId);
    
    // Save conversation with new key structure: conversation:{userId}:{conversationId}
    await kv.set(`conversation:${user.id}:${conversationId}`, conversation);
    
    // Add to user's conversation list
    await kv.set(userConversationsKey, [conversationId, ...existingConversations]);

    console.log("Conversation created successfully");
    return c.json({ conversation });
  } catch (error) {
    console.log("Create conversation error:", error);
    return c.json({ error: `Failed to create conversation: ${error.message}` }, 500);
  }
});

// Get user's conversations
app.get("/make-server-f876292a/conversations", async (c) => {
  try {
    const user = await verifyAuth(c.req.header("Authorization"));
    if (!user) {
      return c.json({ error: "Unauthorized" }, 401);
    }

    console.log("Getting conversations for user:", user.id);
    const conversationIds = await kv.get(`conversations:${user.id}`) || [];
    console.log("Conversation IDs:", conversationIds);
    
    if (conversationIds.length === 0) {
      return c.json({ conversations: [] });
    }
    
    // Use mget for better performance - fetch all conversations at once
    const conversationKeys = conversationIds.map((id: string) => `conversation:${user.id}:${id}`);
    const conversations = await kv.mget(conversationKeys);

    const validConversations = conversations.filter(Boolean).map(conv => ({
      id: conv.id,
      userId: conv.userId,
      title: conv.title,
      createdAt: conv.createdAt,
      updatedAt: conv.updatedAt,
      // messages는 대화방 목록에서는 제외
    }));
    console.log("Valid conversations:", validConversations.length);
    return c.json({ conversations: validConversations });
  } catch (error) {
    console.log("Get conversations error:", error);
    return c.json({ error: `Failed to get conversations: ${error.message}` }, 500);
  }
});

// Delete conversation
app.delete("/make-server-f876292a/conversations/:id", async (c) => {
  try {
    const user = await verifyAuth(c.req.header("Authorization"));
    if (!user) {
      return c.json({ error: "Unauthorized" }, 401);
    }

    const conversationId = c.req.param("id");
    const conversation = await kv.get(`conversation:${user.id}:${conversationId}`);

    if (!conversation || conversation.userId !== user.id) {
      return c.json({ error: "Conversation not found or unauthorized" }, 404);
    }

    console.log("Deleting conversation:", conversationId);
    
    // Delete conversation (messages and feedback are included in the conversation object)
    await kv.del(`conversation:${user.id}:${conversationId}`);
    
    // Remove from user's list
    const userConversationsKey = `conversations:${user.id}`;
    const conversations = await kv.get(userConversationsKey) || [];
    await kv.set(userConversationsKey, conversations.filter((id: string) => id !== conversationId));

    console.log("Conversation deleted successfully");
    return c.json({ success: true });
  } catch (error) {
    console.log("Delete conversation error:", error);
    return c.json({ error: `Failed to delete conversation: ${error.message}` }, 500);
  }
});

// Save message
app.post("/make-server-f876292a/messages", async (c) => {
  try {
    const user = await verifyAuth(c.req.header("Authorization"));
    if (!user) {
      return c.json({ error: "Unauthorized" }, 401);
    }

    const { conversationId, message } = await c.req.json();
    
    console.log("Saving message to conversation:", conversationId);
    
    // Verify conversation ownership and get conversation
    const conversationKey = `conversation:${user.id}:${conversationId}`;
    const conversation = await kv.get(conversationKey);
    if (!conversation || conversation.userId !== user.id) {
      console.log("Conversation not found or unauthorized");
      return c.json({ error: "Conversation not found or unauthorized" }, 404);
    }

    // Add new message to conversation's messages array
    if (!conversation.messages) {
      conversation.messages = [];
    }
    conversation.messages.push(message);

    // Update conversation timestamp
    conversation.updatedAt = new Date().toISOString();
    
    // Save updated conversation
    await kv.set(conversationKey, conversation);

    console.log("Message saved successfully. Total messages:", conversation.messages.length);
    return c.json({ success: true, message });
  } catch (error) {
    console.log("Save message error:", error);
    return c.json({ error: `Failed to save message: ${error.message}` }, 500);
  }
});

// Get messages for a conversation
app.get("/make-server-f876292a/messages/:conversationId", async (c) => {
  try {
    const user = await verifyAuth(c.req.header("Authorization"));
    if (!user) {
      console.log("Get messages: Unauthorized - no user");
      return c.json({ error: "Unauthorized" }, 401);
    }

    const conversationId = c.req.param("conversationId");
    console.log("Getting messages for conversation:", conversationId, "user:", user.id);
    
    const conversation = await kv.get(`conversation:${user.id}:${conversationId}`);
    console.log("Conversation found:", conversation ? "yes" : "no");

    if (!conversation) {
      console.log("Conversation not found:", conversationId);
      return c.json({ error: "Conversation not found" }, 404);
    }

    if (conversation.userId !== user.id) {
      console.log("Unauthorized access attempt by user:", user.id, "for conversation owned by:", conversation.userId);
      return c.json({ error: "Unauthorized access to conversation" }, 403);
    }

    const messages = conversation.messages || [];
    console.log("Messages loaded:", messages.length);
    return c.json({ messages });
  } catch (error) {
    console.log("Get messages error:", error);
    return c.json({ error: `Failed to get messages: ${error.message}` }, 500);
  }
});

// Save feedback (for messages in conversations)
app.post("/make-server-f876292a/feedback", async (c) => {
  try {
    const user = await verifyAuth(c.req.header("Authorization"));
    if (!user) {
      return c.json({ error: "Unauthorized" }, 401);
    }

    const { messageId, conversationId, rating } = await c.req.json();
    
    // Verify conversation ownership and get conversation
    const conversationKey = `conversation:${user.id}:${conversationId}`;
    const conversation = await kv.get(conversationKey);
    if (!conversation || conversation.userId !== user.id) {
      return c.json({ error: "Conversation not found or unauthorized" }, 404);
    }

    // Find the message and add feedback to it
    const messageIndex = conversation.messages.findIndex((msg: any) => msg.id === messageId);
    if (messageIndex === -1) {
      return c.json({ error: "Message not found" }, 404);
    }

    const feedback = {
      rating, // 'positive' or 'negative'
      createdAt: new Date().toISOString(),
    };

    // Add feedback to the message
    conversation.messages[messageIndex].feedback = feedback;
    
    // Save updated conversation
    await kv.set(conversationKey, conversation);

    return c.json({ success: true, feedback });
  } catch (error) {
    console.log("Save feedback error:", error);
    return c.json({ error: `Failed to save feedback: ${error.message}` }, 500);
  }
});

// Save general feedback (for quick questions or general feedback)
app.post("/make-server-f876292a/general-feedback", async (c) => {
  try {
    const user = await verifyAuth(c.req.header("Authorization"));
    if (!user) {
      return c.json({ error: "Unauthorized" }, 401);
    }

    const { content, type } = await c.req.json();
    
    const feedbackId = crypto.randomUUID();
    const feedback = {
      id: feedbackId,
      userId: user.id,
      userEmail: user.email,
      content,
      type: type || 'general', // 'general', 'quick_question_feedback', etc.
      createdAt: new Date().toISOString(),
    };

    // Save to general feedback list
    await kv.set(`feedback:${feedbackId}`, feedback);
    
    // Add to all feedbacks list
    const allFeedbacks = await kv.get('feedbacks:all') || [];
    await kv.set('feedbacks:all', [feedbackId, ...allFeedbacks]);

    console.log("General feedback saved:", feedbackId);
    return c.json({ success: true, feedback });
  } catch (error) {
    console.log("Save general feedback error:", error);
    return c.json({ error: `Failed to save feedback: ${error.message}` }, 500);
  }
});

// Get all general feedbacks (admin only)
app.get("/make-server-f876292a/admin/feedbacks", async (c) => {
  try {
    const user = await verifyAuth(c.req.header("Authorization"));
    if (!user) {
      return c.json({ error: "Unauthorized" }, 401);
    }

    // Check if user is admin
    if (user.email !== "khb1620@naver.com") {
      return c.json({ error: "Forbidden: Admin access only" }, 403);
    }

    const feedbackIds = await kv.get('feedbacks:all') || [];
    
    if (feedbackIds.length === 0) {
      return c.json({ feedbacks: [] });
    }
    
    // Use mget for better performance - fetch all feedbacks at once
    const feedbackKeys = feedbackIds.map((id: string) => `feedback:${id}`);
    const feedbacks = await kv.mget(feedbackKeys);

    const validFeedbacks = feedbacks.filter(Boolean);
    
    return c.json({ feedbacks: validFeedbacks });
  } catch (error) {
    console.log("Get feedbacks error:", error);
    return c.json({ error: `Failed to get feedbacks: ${error.message}` }, 500);
  }
});

// Get feedback for a message
app.get("/make-server-f876292a/feedback/:messageId", async (c) => {
  try {
    const user = await verifyAuth(c.req.header("Authorization"));
    if (!user) {
      return c.json({ error: "Unauthorized" }, 401);
    }

    const messageId = c.req.param("messageId");
    
    // Get all conversations for the user and find the message
    const conversationIds = await kv.get(`conversations:${user.id}`) || [];
    
    for (const convId of conversationIds) {
      const conversation = await kv.get(`conversation:${user.id}:${convId}`);
      if (conversation && conversation.messages) {
        const message = conversation.messages.find((msg: any) => msg.id === messageId);
        if (message && message.feedback) {
          return c.json({ feedback: message.feedback });
        }
      }
    }

    return c.json({ feedback: null });
  } catch (error) {
    console.log("Get feedback error:", error);
    return c.json({ error: `Failed to get feedback: ${error.message}` }, 500);
  }
});

// Delete user account
app.delete("/make-server-f876292a/user/delete", async (c) => {
  try {
    const user = await verifyAuth(c.req.header("Authorization"));
    if (!user) {
      return c.json({ error: "Unauthorized" }, 401);
    }

    console.log("Deleting account for user:", user.id);

    // Delete all conversations
    const conversationIds = await kv.get(`conversations:${user.id}`) || [];
    const conversationKeys = conversationIds.map((id: string) => `conversation:${user.id}:${id}`);
    
    if (conversationKeys.length > 0) {
      await kv.mdel(conversationKeys);
    }
    
    // Delete conversation list
    await kv.del(`conversations:${user.id}`);

    // Delete quick questions
    await kv.del(`quickQuestions:${user.id}`);

    // Delete user from Supabase Auth
    const supabase = createClient(
      Deno.env.get("SUPABASE_URL"),
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY"),
    );
    
    const { error: deleteError } = await supabase.auth.admin.deleteUser(user.id);
    
    if (deleteError) {
      console.log("Error deleting user from auth:", deleteError);
      return c.json({ error: `Failed to delete user: ${deleteError.message}` }, 500);
    }

    console.log("User account deleted successfully:", user.id);
    return c.json({ success: true });
  } catch (error) {
    console.log("Delete account error:", error);
    return c.json({ error: `Failed to delete account: ${error.message}` }, 500);
  }
});

// Save quick question (question-answer pair)
app.post("/make-server-f876292a/quick-question", async (c) => {
  try {
    const user = await verifyAuth(c.req.header("Authorization"));
    if (!user) {
      return c.json({ error: "Unauthorized" }, 401);
    }

    const { questionId, question, answer, timestamp } = await c.req.json();
    
    console.log("Saving quick question for user:", user.id);

    const key = `quickQuestions:${user.id}`;
    const questions = await kv.get(key) || [];
    
    questions.push({
      id: questionId,
      question,
      answer,
      timestamp,
      feedback: null
    });

    await kv.set(key, questions);
    
    console.log("Quick question saved successfully");
    return c.json({ success: true });
  } catch (error) {
    console.log("Save quick question error:", error);
    return c.json({ error: `Failed to save quick question: ${error.message}` }, 500);
  }
});

// Get quick questions
app.get("/make-server-f876292a/quick-questions", async (c) => {
  try {
    const user = await verifyAuth(c.req.header("Authorization"));
    if (!user) {
      return c.json({ error: "Unauthorized" }, 401);
    }

    console.log("Getting quick questions for user:", user.id);

    const key = `quickQuestions:${user.id}`;
    const questions = await kv.get(key) || [];
    
    console.log("Quick questions loaded:", questions.length);
    return c.json({ questions });
  } catch (error) {
    console.log("Get quick questions error:", error);
    return c.json({ error: `Failed to get quick questions: ${error.message}` }, 500);
  }
});

// Save feedback for quick question
app.post("/make-server-f876292a/quick-question-feedback", async (c) => {
  try {
    const user = await verifyAuth(c.req.header("Authorization"));
    if (!user) {
      return c.json({ error: "Unauthorized" }, 401);
    }

    const { questionId, rating } = await c.req.json();
    
    console.log("Saving quick question feedback for user:", user.id, "question:", questionId);

    const key = `quickQuestions:${user.id}`;
    const questions = await kv.get(key) || [];
    
    const questionIndex = questions.findIndex((q: any) => q.id === questionId);
    
    if (questionIndex === -1) {
      console.log("Quick question not found:", questionId);
      return c.json({ error: "Question not found" }, 404);
    }

    questions[questionIndex].feedback = rating;
    await kv.set(key, questions);
    
    console.log("Quick question feedback saved successfully");
    return c.json({ success: true });
  } catch (error) {
    console.log("Save quick question feedback error:", error);
    return c.json({ error: `Failed to save feedback: ${error.message}` }, 500);
  }
});

Deno.serve(app.fetch);
