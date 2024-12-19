package payload

type EtcdMemberListOut struct {
	Header  EtcdMemberListResponseHeader   `json:"header"`
	Members []EtcdMemberListResponseMember `json:"members"`
}

type EtcdMemberListResponseHeader struct {
	ClusterID uint64 `json:"cluster_id"`
	MemberID  uint64 `json:"member_id"`
	RaftTerm  uint64 `json:"raft_term"`
}

type EtcdMemberListResponseMember struct {
	ID         uint64   `json:"ID"`
	Name       string   `json:"name"`
	PeerURLs   []string `json:"peerURLs"`
	ClientURLs []string `json:"clientURLs"`
}
