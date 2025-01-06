# delete worker node (data node)

set vars

```bash
dad_id= # ex 122
child_id= # ex 130
```

steps

```bash
go run . vm kubectl drain --dad-id $dad_id --child-id $child_id
go run . vm kubectl delete node --dad-id $dad_id --child-id $child_id
go run . vm shutdown --vmid $child_id
go run . vm delete --vmid $child_id
```
